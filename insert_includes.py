"""트레이스 전처리: include 디펜던시를 Traces/<webapp>의 트레이스 파일에 직접 삽입.

Includes/<webapp>.xlsx의 Sheet1을 위 행부터 순서대로 보면서, 파일에 Source가 있으면 Target을 파일 끝에 추가
(앞 행에서 추가된 Target도 뒤 행의 Source가 될 수 있음). 이미 있는 Target은 추가하지 않으므로 여러 번 돌려도 결과는 같음.

원본 트레이스가 변경되므로 대상 웹 앱을 직접 지정해야 함.

사용법:
    python insert_includes.py PetClinic
"""
import argparse
from pathlib import Path

import openpyxl

from usecase_matrix_common import ARCHIVE_ROOT, TRACES_DIR, is_hidden, read_components

INCLUDES_DIR = ARCHIVE_ROOT / 'Includes'


def load_include_relation(path: Path) -> list[tuple[str, str]]:
    """엑셀 행 순서대로의 (Source, Target) 목록."""
    ws = openpyxl.load_workbook(path, read_only=True)['Sheet1']
    rows = ws.iter_rows(values_only=True)
    header = [str(h).strip() for h in next(rows)]
    src_idx, tgt_idx = header.index('Source'), header.index('Target')

    relation = []
    for row in rows:
        source, target = row[src_idx], row[tgt_idx]
        if source and target:
            relation.append((str(source).strip(), str(target).strip()))
    return relation


def insert_includes(txt_path: Path, relation: list[tuple[str, str]]) -> list[str]:
    """트레이스 파일 하나에 빠진 Target을 삽입하고, 삽입한 Target 목록을 돌려줌."""
    comps = read_components(txt_path)
    targets = []
    for source, target in relation:
        if source in comps and target not in comps:
            comps.add(target)
            targets.append(target)
    if not targets:
        return targets

    content = txt_path.read_bytes()
    newline = b'\r\n' if b'\r\n' in content else b'\n'
    with txt_path.open('ab') as f:
        # 마지막 줄에 개행이 없으면 Target이 그 줄에 붙으므로 먼저 개행
        if content and not content.endswith(b'\n'):
            f.write(newline)
        for target in targets:
            f.write(target.encode('utf-8') + newline)
    return targets


def main():
    webapps_available = sorted(p.stem for p in INCLUDES_DIR.glob('*.xlsx')
                               if (TRACES_DIR / p.stem).is_dir())
    parser = argparse.ArgumentParser(description='include 디펜던시를 트레이스 파일에 삽입 (원본 변경)')
    parser.add_argument('webapps', nargs='+', help=f"대상 웹 앱 (가능: {', '.join(webapps_available)})")
    args = parser.parse_args()

    unknown = [w for w in args.webapps if w not in webapps_available]
    if unknown:
        parser.error(f"알 수 없는 웹 앱: {', '.join(unknown)} (가능: {', '.join(webapps_available)})")

    for webapp in args.webapps:
        relation = load_include_relation(INCLUDES_DIR / f'{webapp}.xlsx')
        app_dir = TRACES_DIR / webapp
        total = changed = inserted = 0
        for txt in sorted(app_dir.rglob('*.txt')):
            if is_hidden(txt, app_dir):
                continue
            total += 1
            targets = insert_includes(txt, relation)
            changed += bool(targets)
            inserted += len(targets)
        print(f'[{webapp}] files={total} changed={changed} inserted={inserted}')


if __name__ == '__main__':
    main()
