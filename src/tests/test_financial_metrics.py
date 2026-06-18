import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.tools.risk_score import FinancialRiskScore
from src.database.sec_repository import SECRepository
from src.tools.financial_ratios import FinancialRatios

def main():
    ticker = "AAPL"
    repository = SECRepository()
    metrics = repository.get_metrics(ticker)

    if not metrics:
        raise ValueError(
            f"No SEC metrics found for ticker {ticker}"
        )

    ratios = FinancialRatios(metrics).calculate()

    metric_map = {
        metric["metric_name"]: metric["value"]
        for metric in metrics
    }

    risk_result = FinancialRiskScore(
        ratios=ratios,
        metrics=metric_map,
    ).calculate()

    print("=" * 80)
    print(f"FINANCIAL ANALYSIS - {ticker}")
    print("=" * 80)

    print("\nFINANCIAL RATIOS")
    print("-" * 80)

    for ratio_name, value in ratios.items():
        print(f"{ratio_name:<30} {value}")

    print("\nRISK SCORE")
    print("-" * 80)

    print(
        f"Risk Score: "
        f"{risk_result['risk_score']:.2f}"
        if risk_result["risk_score"] is not None
        else "Risk Score: N/A"
    )

    print(f"Risk Level: {risk_result['risk_level']}")

    print("\nCOMPONENTS")
    print("-" * 80)

    for component_name, component in risk_result["components"].items():

        print()
        print(f"{component_name.upper()}")

        print(
            f"Score: "
            f"{component['score']:.2f}"
            if component["score"] is not None
            else "Score: N/A"
        )

        metrics_dict = component.get("metrics", {})

        if metrics_dict:
            print("Metrics:")

            for metric_name, value in metrics_dict.items():
                print(f"  {metric_name:<35} {value}")

        signals = component.get("signals", [])

        if signals:
            print("Signals:")

            for signal in signals:
                print(f"  - {signal}")

    print("\nWEIGHTS")
    print("-" * 80)

    for component, weight in risk_result["weights"].items():
        print(f"{component:<20} {weight:.2%}")

    print()
    print("=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()