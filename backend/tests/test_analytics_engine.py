"""
Analytics engine unit tests - tests pure analytics independently of FastAPI/DB.
SRS Reference: FR-04, Section 12.A
"""
import pytest
from app.analytics.metrics import (
    SectionData, compute_section_utilization, compute_weighted_utilization,
    compute_full_capacity_rate, compute_demand_trend, compute_unmet_demand, compute_course_metrics,
)
from app.analytics.demand_engine import DemandEngine, AnalysisParameters


class TestSectionUtilization:
    def test_normal_case(self):
        assert compute_section_utilization(24, 30) == pytest.approx(80.0)

    def test_full_capacity(self):
        assert compute_section_utilization(30, 30) == pytest.approx(100.0)

    def test_over_capacity(self):
        assert compute_section_utilization(35, 30) == pytest.approx(116.67, rel=0.01)

    def test_zero_capacity_returns_none(self):
        assert compute_section_utilization(20, 0) is None

    def test_negative_capacity_returns_none(self):
        assert compute_section_utilization(20, -5) is None

    def test_none_enrollment_returns_none(self):
        assert compute_section_utilization(None, 30) is None

    def test_none_capacity_returns_none(self):
        assert compute_section_utilization(20, None) is None

    def test_zero_enrollment(self):
        assert compute_section_utilization(0, 30) == pytest.approx(0.0)


class TestWeightedUtilization:
    def test_weighted_not_average(self):
        # (20+28)/(40+30)*100 = 68.57%, not average of 50% and 93.3%
        sections = [
            SectionData("CS-101", "Fall 2023", 2023, enrollment=20, capacity=40),
            SectionData("CS-101", "Spring 2024", 2024, enrollment=28, capacity=30),
        ]
        result = compute_weighted_utilization(sections)
        assert result == pytest.approx(48 / 70 * 100, rel=0.001)

    def test_excludes_zero_capacity(self):
        sections = [
            SectionData("CS-101", "Fall 2023", 2023, enrollment=20, capacity=30),
            SectionData("CS-101", "Spring 2024", 2024, enrollment=10, capacity=0),
        ]
        assert compute_weighted_utilization(sections) == pytest.approx(20 / 30 * 100)

    def test_all_missing_returns_none(self):
        sections = [SectionData("CS-101", "Fall 2023", 2023, enrollment=None, capacity=None)]
        assert compute_weighted_utilization(sections) is None

    def test_empty_returns_none(self):
        assert compute_weighted_utilization([]) is None


class TestFullCapacityRate:
    def test_all_full(self):
        sections = [
            SectionData("CS-101", "Fall 2020", 2020, enrollment=30, capacity=30),
            SectionData("CS-101", "Fall 2021", 2021, enrollment=29, capacity=30),
        ]
        count, rate = compute_full_capacity_rate(sections)
        assert count == 2
        assert rate == pytest.approx(1.0)

    def test_half_full(self):
        sections = [
            SectionData("CS-101", "Fall 2020", 2020, enrollment=30, capacity=30),
            SectionData("CS-101", "Fall 2021", 2021, enrollment=20, capacity=30),
        ]
        count, rate = compute_full_capacity_rate(sections)
        assert count == 1
        assert rate == pytest.approx(0.5)

    def test_no_valid_sections(self):
        sections = [SectionData("CS-101", "Fall 2020", 2020, enrollment=None, capacity=30)]
        count, rate = compute_full_capacity_rate(sections)
        assert count is None and rate is None


class TestDemandTrend:
    def test_increasing_trend(self):
        sections = [
            SectionData("CS-101", "Fall 2020", 2020, enrollment=20, capacity=40),
            SectionData("CS-101", "Fall 2021", 2021, enrollment=25, capacity=40),
            SectionData("CS-101", "Fall 2022", 2022, enrollment=30, capacity=40),
            SectionData("CS-101", "Fall 2023", 2023, enrollment=35, capacity=40),
        ]
        trend, slope, r2 = compute_demand_trend(sections, min_terms=2)
        assert trend == "INCREASING"
        assert slope > 2.0

    def test_decreasing_trend(self):
        sections = [
            SectionData("CS-101", "Fall 2020", 2020, enrollment=40, capacity=40),
            SectionData("CS-101", "Fall 2021", 2021, enrollment=33, capacity=40),
            SectionData("CS-101", "Fall 2022", 2022, enrollment=26, capacity=40),
            SectionData("CS-101", "Fall 2023", 2023, enrollment=20, capacity=40),
        ]
        trend, slope, r2 = compute_demand_trend(sections, min_terms=2)
        assert trend == "DECREASING"
        assert slope < -2.0

    def test_stable_trend(self):
        sections = [
            SectionData("CS-101", "Fall 2020", 2020, enrollment=25, capacity=40),
            SectionData("CS-101", "Fall 2021", 2021, enrollment=26, capacity=40),
            SectionData("CS-101", "Fall 2022", 2022, enrollment=24, capacity=40),
        ]
        trend, slope, r2 = compute_demand_trend(sections, min_terms=2)
        assert trend == "STABLE"

    def test_insufficient_data(self):
        sections = [SectionData("CS-101", "Fall 2020", 2020, enrollment=25, capacity=40)]
        trend, slope, r2 = compute_demand_trend(sections, min_terms=2)
        assert trend == "INSUFFICIENT_DATA"
        assert slope is None


class TestUnmetDemand:
    def test_direct_field(self):
        sections = [
            SectionData("CS-101", "Fall 2020", 2020, enrollment=28, capacity=30, unmet_demand=5),
            SectionData("CS-101", "Fall 2021", 2021, enrollment=30, capacity=30, unmet_demand=8),
        ]
        has_data, avg, total = compute_unmet_demand(sections)
        assert has_data is True
        assert total == 13
        assert avg == pytest.approx(6.5)

    def test_from_attempted_enrollment(self):
        sections = [SectionData("CS-101", "Fall 2020", 2020, enrollment=28, capacity=30, attempted_enrollment=33)]
        has_data, avg, total = compute_unmet_demand(sections)
        assert has_data is True
        assert total == 5

    def test_not_inferred_from_enrollment_alone(self):
        sections = [SectionData("CS-101", "Fall 2020", 2020, enrollment=30, capacity=30)]
        has_data, avg, total = compute_unmet_demand(sections)
        assert has_data is False
        assert avg is None
        assert total is None


class TestDemandEngine:
    def _params(self):
        return AnalysisParameters(
            high_utilization_threshold=85.0,
            low_utilization_threshold=50.0,
            full_capacity_threshold=0.95,
            frequently_full_threshold=0.50,
            increasing_demand_slope=2.0,
            min_terms_for_trend=2,
        )

    def test_empty_input(self):
        engine = DemandEngine(self._params())
        result = engine.analyze([])
        assert result.total_courses == 0

    def test_high_utilization_rec(self):
        sections = [
            SectionData("CS-HIGH", "Fall 2020", 2020, enrollment=28, capacity=30),
            SectionData("CS-HIGH", "Fall 2021", 2021, enrollment=29, capacity=30),
            SectionData("CS-HIGH", "Fall 2022", 2022, enrollment=30, capacity=30),
        ]
        result = DemandEngine(self._params()).analyze(sections)
        assert result.course_metrics["CS-HIGH"].avg_utilization_pct > 85
        categories = [r.category for r in result.recommendations]
        assert "consider_adding_section" in categories

    def test_low_utilization_rec(self):
        sections = [
            SectionData("CS-LOW", "Fall 2020", 2020, enrollment=10, capacity=40),
            SectionData("CS-LOW", "Fall 2021", 2021, enrollment=12, capacity=40),
            SectionData("CS-LOW", "Fall 2022", 2022, enrollment=11, capacity=40),
        ]
        result = DemandEngine(self._params()).analyze(sections)
        m = result.course_metrics["CS-LOW"]
        # (10+12+11)/(40*3)*100 = 27.5%
        assert m.avg_utilization_pct == pytest.approx(33/120*100, rel=0.01)
        assert "review_low_utilization" in [r.category for r in result.recommendations]

    def test_deterministic(self):
        sections = [
            SectionData("CS-101", "Fall 2020", 2020, enrollment=25, capacity=30),
            SectionData("CS-101", "Fall 2021", 2021, enrollment=27, capacity=30),
        ]
        engine = DemandEngine(self._params())
        r1 = engine.analyze(sections)
        r2 = engine.analyze(sections)
        assert r1.course_metrics["CS-101"].avg_utilization_pct == r2.course_metrics["CS-101"].avg_utilization_pct
        assert r1.course_metrics["CS-101"].demand_trend == r2.course_metrics["CS-101"].demand_trend

    def test_zero_capacity_excluded_from_utilization(self):
        sections = [
            SectionData("CS-101", "Fall 2020", 2020, enrollment=20, capacity=0),
            SectionData("CS-101", "Fall 2021", 2021, enrollment=20, capacity=30),
        ]
        result = DemandEngine(self._params()).analyze(sections)
        m = result.course_metrics["CS-101"]
        assert m.avg_utilization_pct == pytest.approx(20/30*100, rel=0.01)

    def test_none_enrollment_not_zero(self):
        sections = [
            SectionData("CS-101", "Fall 2020", 2020, enrollment=None, capacity=30),
            SectionData("CS-101", "Fall 2021", 2021, enrollment=24, capacity=30),
        ]
        result = DemandEngine(self._params()).analyze(sections)
        m = result.course_metrics["CS-101"]
        assert m.avg_enrollment == pytest.approx(24.0)

    def test_scenario_does_not_modify_baseline(self):
        original = [
            SectionData("CS-101", "Fall 2020", 2020, enrollment=25, capacity=30),
            SectionData("CS-101", "Fall 2021", 2021, enrollment=27, capacity=30),
        ]
        engine = DemandEngine(self._params())
        baseline = engine.analyze(original)
        modified = [
            SectionData("CS-101", "Fall 2020", 2020, enrollment=25, capacity=40),
            SectionData("CS-101", "Fall 2021", 2021, enrollment=27, capacity=40),
        ]
        comparison = engine.compare_scenario(baseline, modified, "change_capacity", {"course_id": "CS-101", "new_capacity": 40})
        # Baseline must not change
        assert baseline.course_metrics["CS-101"].avg_utilization_pct == pytest.approx((25+27)/(30+30)*100, rel=0.01)
        assert comparison["is_simulated"] is True
