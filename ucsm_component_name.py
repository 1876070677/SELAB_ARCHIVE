"""UCSM 실험 재현: 컴포넌트 이름과 유스케이스 명세의 임베딩 유사도로 컴포넌트를 유스케이스에 매핑.

- UsecaseDescription/<webapp>_UseCaseDescription.xlsx : 유스케이스별 명세 (Description 열)
- UCSM_(component-name)_stopwords/stoplist2.txt      : 불용어 (USE_STOPLIST2 웹 앱에만 적용)
- GroundTruth/<webapp>_ans.csv                        : 컴포넌트별 정답 클러스터 (-1: 유틸리티)

결과:
- Reproduction/UCSM_(component-name)/<webapp>.csv : 컴포넌트별 예측 (cluster는 명세 파일의 유스케이스 순서)
- Reproduction/UCSM_(component-name)/metrics.csv  : 웹 앱별 Accuracy, Macro-F1 (실행한 웹 앱의 행만 갱신)

사용법:
    python ucsm_component_name.py                # 전체 웹 앱
    python ucsm_component_name.py DayTrader      # 특정 웹 앱만
    python ucsm_component_name.py JPetStore2 PetClinic -o ./out
"""
import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim
from sklearn.metrics import f1_score

ARCHIVE_ROOT = Path(__file__).resolve().parent
DESCRIPTIONS_DIR = ARCHIVE_ROOT / 'UsecaseDescription'
STOPLIST_PATH = ARCHIVE_ROOT / 'UCSM_(component-name)_stopwords' / 'stoplist2.txt'
GROUNDTRUTH_DIR = ARCHIVE_ROOT / 'GroundTruth'

MODEL_NAME = 'multi-qa-distilbert-cos-v1'
WEBAPPS = ['JPetStore2', 'JPetStore6', 'PetClinic', 'ShoppingApp', 'DayTrader']
# 불용어를 적용하는 웹 앱 (나머지는 불용어 없이 재현됨)
USE_STOPLIST2 = {'JPetStore2', 'PetClinic', 'ShoppingApp'}


def load_stopwords(webapp: str) -> set[str]:
    if webapp not in USE_STOPLIST2:
        return set()
    with STOPLIST_PATH.open(encoding='utf-8') as f:
        return {line.strip().lower() for line in f}


def tokenize(component: str, stopwords: set[str]) -> list[str]:
    """컴포넌트 이름 -> 종류 표기 제거, 카멜/스네이크 케이스 분리, 소문자화, 불용어 제거."""
    name = re.sub(r'\((table|xhtml|html|jsp)\)', '', component)
    parts = re.split(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|(?=[A-Z][a-z])|(?<=\\d)(?=\\D)|(?=\\d)(?<=\\D)|[_]', name)
    return [p.lower() for p in parts if p and p.lower() not in stopwords]


def embed_usecases(encode, webapp: str) -> tuple[list[str], np.ndarray]:
    """명세를 문장으로 나눠 각 문장과 유스케이스 이름을 임베딩한 뒤 평균."""
    df = pd.read_excel(DESCRIPTIONS_DIR / f'{webapp}_UseCaseDescription.xlsx', index_col=0)
    names, embeddings = [], []
    for usecase, description in df['Description'].items():
        sentences = [s + '.' for s in description.split('.') if s]
        sentences.append(usecase)
        names.append(usecase)
        embeddings.append(np.mean([encode(s) for s in sentences], axis=0))
    return names, np.array(embeddings)


def predict(encode, components: list[str], usecase_embeddings: np.ndarray, stopwords: set[str]) -> list[int]:
    predictions = []
    for component in components:
        tokens = tokenize(component, stopwords)
        if not tokens:
            # 불용어로 토큰이 모두 사라지면 유사도를 구할 수 없어 첫 번째 유스케이스로 분류
            predictions.append(0)
            continue
        component_embedding = np.mean([encode(t) for t in tokens], axis=0)
        predictions.append(int(np.argmax(cos_sim(usecase_embeddings, component_embedding).numpy()[:, 0])))
    return predictions


def evaluate(answers: list[int], predictions: list[int]) -> tuple[float, float]:
    """유틸리티(-1) 컴포넌트는 어느 유스케이스로 분류해도 정답으로 처리."""
    utility = len(set(answers))
    correct = sum(a == -1 or a == p for a, p in zip(answers, predictions))
    y_true = [utility if a == -1 else a for a in answers]
    y_pred = [utility if a == -1 else p for a, p in zip(answers, predictions)]
    return correct / len(answers), f1_score(y_true, y_pred, average='macro')


def run(encode, webapp: str, out_dir: Path) -> dict:
    ground_truth = pd.read_csv(GROUNDTRUTH_DIR / f'{webapp}_ans.csv')
    components = ground_truth['ans_class'].tolist()
    answers = ground_truth['ans_cluster'].tolist()

    usecases, usecase_embeddings = embed_usecases(encode, webapp)
    stopwords = load_stopwords(webapp)
    predictions = predict(encode, components, usecase_embeddings, stopwords)
    accuracy, macro_f1 = evaluate(answers, predictions)

    pd.DataFrame({'component': components, 'cluster': predictions,
                  'usecase': [usecases[p] for p in predictions], 'ground_truth': answers}
                 ).to_csv(out_dir / f'{webapp}.csv', index=False)

    stoplist = 'stoplist2' if stopwords else 'none'
    print(f'[{webapp}] stopwords={stoplist} accuracy={accuracy:.3f} macro_f1={macro_f1:.3f}')
    return {'webapp': webapp, 'stopwords': stoplist, 'accuracy': accuracy, 'macro_f1': macro_f1}


def main():
    parser = argparse.ArgumentParser(description='UCSM 실험 재현 (컴포넌트 이름 임베딩)')
    parser.add_argument('webapps', nargs='*', help=f"대상 웹 앱 (생략 시 전체: {', '.join(WEBAPPS)})")
    parser.add_argument('-o', '--out-dir', type=Path, default=ARCHIVE_ROOT / 'Reproduction' / 'UCSM_(component-name)',
                        help='결과 저장 폴더 (기본: Reproduction/UCSM_(component-name))')
    args = parser.parse_args()

    webapps = args.webapps or WEBAPPS
    unknown = [w for w in webapps if w not in WEBAPPS]
    if unknown:
        parser.error(f"알 수 없는 웹 앱: {', '.join(unknown)} (가능: {', '.join(WEBAPPS)})")

    model = SentenceTransformer(MODEL_NAME)
    cache = {}

    def encode(text: str) -> np.ndarray:
        if text not in cache:
            cache[text] = model.encode(text)
        return cache[text]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = [run(encode, webapp, args.out_dir) for webapp in webapps]

    metrics_path = args.out_dir / 'metrics.csv'
    metrics = pd.DataFrame(rows)
    if metrics_path.exists():
        previous = pd.read_csv(metrics_path)
        metrics = pd.concat([previous[~previous['webapp'].isin(webapps)], metrics])
    metrics['order'] = metrics['webapp'].map(WEBAPPS.index)
    metrics.sort_values('order').drop(columns='order').to_csv(metrics_path, index=False)


if __name__ == '__main__':
    main()
