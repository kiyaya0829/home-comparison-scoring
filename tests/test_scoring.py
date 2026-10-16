import copy
import unittest
from unittest.mock import patch
from scoring import ExperimentalPolicy, score


def fixture():
    criteria = [dict(id='t', label='Work', importance='High'),
                dict(id='a', label='Park', importance='Medium')]
    rows = [dict(postal_code=label, metrics={
        't': dict(type='travel', available=True, weekly_minutes=minutes),
        'a': dict(type='amenity', available=True, nearest_metres=distance, count_within_1km=count)
    }) for label, minutes, distance, count in [('A', 150, 1000, 1), ('B', 600, 100, 9)]]
    return rows, criteria


class ScoringTests(unittest.TestCase):
    def test_reference_values_and_monotonicity(self):
        p = ExperimentalPolicy()
        scores = [p.criterion_score(dict(type='travel', available=True, weekly_minutes=b)) for b in [0, 150, 300, 600, 900]]
        self.assertEqual(scores, [100, 100*300/450, 50, 100/3, 25])
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(p.criterion_score(dict(type='amenity', available=True, nearest_metres=500, count_within_1km=3)), 50)

    def test_reranking_is_pure_and_offline(self):
        rows, criteria = fixture()
        original = copy.deepcopy(rows)
        with patch('socket.socket', side_effect=AssertionError('Network forbidden')):
            first = score(rows, criteria)
            changed = copy.deepcopy(criteria)
            changed[0]['importance'], changed[1]['importance'] = 'Low', 'High'
            second = score(rows, changed)
        self.assertEqual(first['rows'][0]['postal_code'], 'A')
        self.assertEqual(second['rows'][0]['postal_code'], 'B')
        self.assertEqual(rows, original)
        self.assertEqual(first, score(rows, criteria))

    def test_coverage_and_missing(self):
        rows, criteria = fixture()
        rows[0]['metrics']['a'] = dict(available=False)
        result = score(rows, criteria)
        self.assertEqual((result['coverage'], result['status']), (50, 'Partial'))
        self.assertEqual(result['highest_fit_candidates'], [])
        self.assertEqual(result['excluded_criteria'], ['a'])
        del rows[1]['metrics']['t']
        result = score(rows, criteria)
        self.assertEqual(result['status'], 'Inconclusive')
        self.assertTrue(all(r['overall'] is None and r['rank'] is None for r in result['rows']))
        self.assertEqual(score([], criteria)['status'], 'Inconclusive')

    def test_ties_and_explanations(self):
        rows, criteria = fixture()
        result = score(rows, criteria)
        for row in result['rows']:
            self.assertAlmostEqual(sum(row['contributions'].values()), row['overall'], places=2)
        delta = sum(result['pairwise'][0]['contribution_differences'].values())
        self.assertAlmostEqual(delta, result['rows'][0]['overall'] - result['rows'][1]['overall'], places=2)
        rows[1]['metrics'] = copy.deepcopy(rows[0]['metrics'])
        result = score(rows, criteria)
        self.assertEqual([r['rank'] for r in result['rows']], [1, 1])
        self.assertEqual(result['highest_fit_candidates'], ['A', 'B'])

    def test_validation_and_zero_count(self):
        for value in [0, -1, float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                ExperimentalPolicy(travel_half=value)
        p = ExperimentalPolicy()
        self.assertEqual(p.criterion_score(dict(type='amenity', available=True, nearest_metres=500, count_within_1km=0)), 25)
        self.assertIsNone(p.criterion_score(dict(available=False)))
        with self.assertRaises(ValueError):
            p.criterion_score(dict(type='travel', available=True, weekly_minutes=-1))


if __name__ == '__main__':
    unittest.main()
