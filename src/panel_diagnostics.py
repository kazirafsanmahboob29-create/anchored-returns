"""Report all planned state omissions rather than selecting favorable exclusions."""

from .panel_models import fit

REGIONAL_RESTRICTIONS = [{"rate_midwest": 1}, {"rate_south": 1}, {"rate_west": 1}]


def state_influence(main, changes, level_features, region_features):
    output = []
    for name, frame, target, features in (
        ("local_state_year", main, "roe", level_features),
        ("regional_slopes", changes, "delta_roe", region_features),
    ):
        for omitted in sorted(frame.state.unique()):
            selected = frame[frame.state != omitted]
            record = {
                "model": name,
                "omitted_state": omitted,
                "n": len(selected),
                "status": "available",
                "prior_coefficient": None,
                "prior_low": None,
                "prior_high": None,
                "regional_test_statistic": None,
                "regional_test_p": None,
                "regional_state_p": None,
                "regional_quarter_p": None,
            }
            try:
                result = fit(selected, target, features, "state_year")
                if name == "local_state_year":
                    coefficient = result.coefficients(["prior"])[0]
                    record.update(
                        prior_coefficient=coefficient["estimate"],
                        prior_low=coefficient["low"],
                        prior_high=coefficient["high"],
                    )
                else:
                    test = result.joint_test(REGIONAL_RESTRICTIONS)
                    record.update(
                        regional_test_statistic=test["statistic"], regional_test_p=test["p"]
                    )
                    record["status"] = test["status"]
                    record["regional_state_p"] = result.joint_test(REGIONAL_RESTRICTIONS, "state")[
                        "p"
                    ]
                    record["regional_quarter_p"] = result.joint_test(
                        REGIONAL_RESTRICTIONS, "quarter"
                    )["p"]
            except ValueError as error:
                record["status"] = str(error)
            output.append(record)
    return output
