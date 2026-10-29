"""유스케이스 행렬 생성 공통 로직.

- Traces/<webapp>/<scenario>/**/*.txt : 시나리오별 실행 컴포넌트 트레이스 (한 줄 = 컴포넌트 1개)
- ScenariosByUsecases/<webapp>.json  : {유스케이스: [시나리오명, ...]}
- Includes/<webapp>.xlsx             : Sheet1의 Source/Target 열 (Source 컴포넌트가 실행되면 Target도 실행된 것으로 간주)
"""
import argparse
import csv
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import openpyxl

ARCHIVE_ROOT = Path(__file__).resolve().parent
TRACES_DIR = ARCHIVE_ROOT / 'Traces'
USECASES_DIR = ARCHIVE_ROOT / 'ScenariosByUsecases'
INCLUDES_DIR = ARCHIVE_ROOT / 'Includes'

# include 디펜던시를 적용하지 않는 웹 앱
NO_INCLUDE_WEBAPPS = {'DayTrader'}


def nfc(s: str) -> str:
    # macOS(NFD)에서 만든 폴더명/시나리오명을 같은 문자열로 비교하기 위해 NFC로 통일
    return unicodedata.normalize('NFC', s)


def available_webapps() -> list[str]:
    return sorted(p.stem for p in USECASES_DIR.glob('*.json'))


def is_hidden(path: Path, base: Path) -> bool:
    # .ipynb_checkpoints, .DS_Store 등 숨김 경로 제외
    return any(part.startswith('.') for part in path.relative_to(base).parts)


def read_components(txt_path: Path) -> set[str]:
    comps = set()
    with txt_path.open(encoding='utf-8', errors='ignore') as f:
        for line in f:
            s = line.strip()
            if s:
                comps.add(s)
    return comps


def load_include_relation(webapp: str) -> dict[str, set[str]]:
    """Source 컴포넌트 -> include하는 Target 컴포넌트 set. 적용 대상이 아니면 빈 dict."""
    if webapp in NO_INCLUDE_WEBAPPS:
        return {}
    path = INCLUDES_DIR / f'{webapp}.xlsx'
    if not path.exists():
        print(f"[WARN] {webapp}: include 파일 없음 -> {path}", file=sys.stderr)
        return {}

    ws = openpyxl.load_workbook(path, read_only=True)['Sheet1']
    rows = ws.iter_rows(values_only=True)
    header = [str(h).strip() for h in next(rows)]
    src_idx, tgt_idx = header.index('Source'), header.index('Target')

    relation = defaultdict(set)
    for row in rows:
        source, target = row[src_idx], row[tgt_idx]
        if source and target:
            relation[str(source).strip()].add(str(target).strip())
    return relation


def expand_includes(comps: set[str], relation: dict[str, set[str]]) -> set[str]:
    """트레이스에 나온 Source 컴포넌트의 Target만 추가 (한 단계만, 연쇄 include는 따라가지 않음)."""
    result = set(comps)
    for comp in comps:
        result |= relation.get(comp, set())
    return result


def load_scenario_components(webapp: str) -> dict[str, set[str]]:
    """시나리오명(NFC) -> 해당 시나리오에서 실행된 컴포넌트 set (include 디펜던시 반영)."""
    app_dir = TRACES_DIR / webapp
    relation = load_include_relation(webapp)
    scenario_to_components = {}
    for d in app_dir.iterdir():
        if not d.is_dir() or d.name.startswith('.'):
            continue
        comps = set()
        for txt in d.rglob('*.txt'):
            if not is_hidden(txt, d):
                comps |= read_components(txt)
        scenario_to_components[nfc(d.name)] = expand_includes(comps, relation)
    return scenario_to_components


def load_usecase_scenarios(webapp: str) -> dict[str, list[str]]:
    with (USECASES_DIR / f'{webapp}.json').open(encoding='utf-8-sig') as f:
        mapping = json.load(f)
    return {usecase: [nfc(s) for s in scenarios] for usecase, scenarios in mapping.items()}


def build_matrix(webapp: str, value_fn) -> tuple[list[str], list[str], list[list]]:
    """컴포넌트 x 유스케이스 행렬 생성.

    value_fn(executed_count, scenario_count) -> 셀 값
    executed_count: 유스케이스의 시나리오 중 해당 컴포넌트가 실행된 시나리오 수
    """
    scenario_to_components = load_scenario_components(webapp)
    usecase_scenarios = load_usecase_scenarios(webapp)

    for usecase, scenarios in usecase_scenarios.items():
        missing = [s for s in scenarios if s not in scenario_to_components]
        for s in missing:
            print(f"[WARN] {webapp}/{usecase}: 트레이스 폴더 없음 -> {s}", file=sys.stderr)

    all_components = set().union(*scenario_to_components.values())
    components = sorted(all_components, key=str.lower)
    usecases = list(usecase_scenarios.keys())

    rows = []
    for comp in components:
        row = [comp]
        for usecase in usecases:
            scenarios = usecase_scenarios[usecase]
            executed = sum(1 for s in scenarios if comp in scenario_to_components.get(s, ()))
            row.append(value_fn(executed, len(scenarios)))
        rows.append(row)
    return components, usecases, rows


def write_csv(out_path: Path, usecases: list[str], rows: list[list]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['component'] + usecases)
        writer.writerows(rows)


def run(description: str, default_out_dir: str, value_fn) -> None:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('webapps', nargs='*',
                        help=f"대상 웹 앱 (생략 시 전체: {', '.join(available_webapps())})")
    parser.add_argument('-o', '--out-dir', type=Path, default=ARCHIVE_ROOT / default_out_dir,
                        help=f'결과 CSV 저장 폴더 (기본: {default_out_dir})')
    args = parser.parse_args()

    webapps = args.webapps or available_webapps()
    unknown = [w for w in webapps if w not in available_webapps()]
    if unknown:
        parser.error(f"알 수 없는 웹 앱: {', '.join(unknown)} (가능: {', '.join(available_webapps())})")

    for webapp in webapps:
        components, usecases, rows = build_matrix(webapp, value_fn)
        out_path = args.out_dir / f'{webapp}.csv'
        write_csv(out_path, usecases, rows)
        include = 'off' if webapp in NO_INCLUDE_WEBAPPS else 'on'
        print(f'[{webapp}] include={include} components={len(components)} usecases={len(usecases)} -> {out_path}')
