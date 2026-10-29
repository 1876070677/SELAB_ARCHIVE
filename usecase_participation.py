"""컴포넌트별 유스케이스 실행 여부 행렬 (1: 유스케이스의 시나리오 중 하나 이상에서 실행, 0: 미실행).

사용법:
    python usecase_participation.py                 # 전체 웹 앱
    python usecase_participation.py DayTrader       # 특정 웹 앱만
    python usecase_participation.py JPetStore2 PetClinic -o ./out
"""
from usecase_matrix_common import run


def participation(executed: int, total: int) -> int:
    return 1 if executed > 0 else 0


if __name__ == '__main__':
    run('컴포넌트별 유스케이스 실행 여부 행렬 생성', 'UsecaseParticipation', participation)
