"""시나리오별 컴포넌트 실행 여부 행렬 (행: 컴포넌트, 열: 시나리오, 1: 실행 / 0: 미실행).

include 디펜던시는 usecase_matrix_common과 동일하게 반영 (DayTrader 제외, 한 단계만).

사용법:
    python components_by_scenario.py                # 전체 웹 앱
    python components_by_scenario.py JPetStore6     # 특정 웹 앱만
    python components_by_scenario.py PetClinic -o ./out
"""
import argparse
from pathlib import Path

from usecase_matrix_common import (ARCHIVE_ROOT, NO_INCLUDE_WEBAPPS, available_webapps,
                                   load_scenario_components, write_csv)


def build(webapp: str) -> tuple[list[str], list[list]]:
    scenario_to_components = load_scenario_components(webapp)
    scenarios = sorted(scenario_to_components, key=str.lower)
    components = sorted(set().union(*scenario_to_components.values()), key=str.lower)
    rows = [[comp] + [1 if comp in scenario_to_components[s] else 0 for s in scenarios]
            for comp in components]
    return scenarios, rows


def main():
    parser = argparse.ArgumentParser(description='시나리오별 컴포넌트 실행 여부 행렬 생성')
    parser.add_argument('webapps', nargs='*',
                        help=f"대상 웹 앱 (생략 시 전체: {', '.join(available_webapps())})")
    parser.add_argument('-o', '--out-dir', type=Path, default=ARCHIVE_ROOT / 'ComponentsByScenarios',
                        help='결과 CSV 저장 폴더 (기본: ComponentsByScenarios)')
    args = parser.parse_args()

    webapps = args.webapps or available_webapps()
    unknown = [w for w in webapps if w not in available_webapps()]
    if unknown:
        parser.error(f"알 수 없는 웹 앱: {', '.join(unknown)} (가능: {', '.join(available_webapps())})")

    for webapp in webapps:
        scenarios, rows = build(webapp)
        out_path = args.out_dir / f'{webapp}.csv'
        write_csv(out_path, scenarios, rows)
        include = 'off' if webapp in NO_INCLUDE_WEBAPPS else 'on'
        print(f'[{webapp}] include={include} components={len(rows)} scenarios={len(scenarios)} -> {out_path}')


if __name__ == '__main__':
    main()
