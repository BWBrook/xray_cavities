import sys
from pathlib import Path

import h5py
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import score_low_power_entropy as score


def synthetic_tables():
    budgets, stages = [], []
    for case, forecasts in score.FORECASTS.items():
        for arm in score.ARMS:
            for i in range(11, 31):
                start, end = 10 + (i - 11)/10, 10 + (i - 10)/10
                label = (end-start)*score.SECONDS_PER_MYR*score.labelled_power(case)
                net = forecasts[int(i > 20)][0] if arm == "ON" else 0.
                residual = net if arm == "ON" else {11: -0.5, 13: -0.00201}.get(i, 0.002)
                common = dict(case=case, arm=arm, start_index=i-1, end_index=i, start_age_myr=start,
                              end_age_myr=end, labelled_energy_erg=label)
                budgets.append(dict(**common, injector_method=score.PRIMARY[0], outer_boundary=score.PRIMARY[1],
                                    time_rule=score.PRIMARY[2], exterior=residual))
                stages.append(dict(**common, region="exterior", entropy_gain_erg=0.1*label,
                                   entropy_with_p_floor_gain_erg=0.02*label, entropy_loss_erg=(net-0.12)*label,
                                   entropy_with_p_floor_loss_erg=0., effective_net_erg=(net+0.01)*label))
    return budgets, stages


def test_registered_counter_and_off_intervals():
    budgets, stages = synthetic_tables()
    annual, off = score.score_tables(budgets, stages)
    assert [r["score"] for r in annual] == ["pass", "pass", "no_annual_forecast"]*2
    assert annual[2]["entropy_net_over_label"] == pytest.approx(0.0385)
    assert annual[2]["all_mapper_net_over_label"] == pytest.approx(0.0485)
    assert annual[2]["exterior_residual_over_label"] == pytest.approx(0.0385)
    assert annual[2]["below_clo_refutation_threshold"] is False
    for case in score.FORECASTS:
        rows = [r for r in off if r["case"] == case]
        assert len(rows) == 20
        assert [r["score"] for r in rows[:3]] == ["excluded_startup", "pass", "miss"]
        assert sum(r["score"] == "pass" for r in rows) == 18
    with pytest.raises(ValueError, match="incomplete"):
        score.score_tables(budgets, stages[:-1])
    with pytest.raises(ValueError, match="duplicated"):
        score.score_tables(budgets + [budgets[-1]], stages)


def test_unequal_input_intervals_and_refutation():
    budgets, stages = synthetic_tables()
    for r in stages:
        if r["case"] == "C-LO":
            r["entropy_loss_erg"] = -0.122*float(r["labelled_energy_erg"])
    annual, _ = score.score_tables(budgets, stages)
    assert [r["below_clo_refutation_threshold"] for r in annual[:3]] == [True]*3
    first, second = budgets[:2]
    a, b = stages[:2]
    first.update(labelled_energy_erg=1., exterior=-0.4)
    second.update(labelled_energy_erg=3., exterior=0.4)
    for r in (a,b):
        r.update(entropy_gain_erg=0., entropy_loss_erg=0., entropy_with_p_floor_gain_erg=0.,
                 entropy_with_p_floor_loss_erg=0., effective_net_erg=0.)
    a["entropy_loss_erg"], b["entropy_gain_erg"] = -0.4, 1.2
    weighted = score.sum_interval_energies([(first, a), (second, b)])
    assert weighted["entropy_net_over_label"] == pytest.approx(0.2)
    assert weighted["exterior_residual_over_label"] == pytest.approx(0.2)


def test_native_header_reads_only_metadata(tmp_path):
    path = tmp_path / "data.0010.flt.h5"
    with h5py.File(path, "w") as f:
        group = f.create_group("Timestep_10")
        group.attrs["Time"] = 3065.5
        for field in score.REQUIRED_DATASETS:
            group.create_dataset(f"vars/{field}", shape=score.FIELD_SHAPE, dtype="<f4", chunks=(1,16,16))
    size = path.stat().st_size
    assert size < 100000
    assert score.header(path, 10, size, 4)["time_code"] == 3065.5
    with pytest.raises(ValueError, match="incomplete native"):
        score.header(path, 10, size-1, 4)
    with pytest.raises(ValueError, match="shape or dtype"):
        score.header(path, 10, size, 8)
