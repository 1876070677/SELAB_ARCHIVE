"""컴포넌트별 유스케이스 실행 비율 행렬 (실행된 시나리오 수 / 유스케이스의 전체 시나리오 수).

사용법:
    python usecase_execution_rate.py                # 전체 웹 앱
    python usecase_execution_rate.py DayTrader      # 특정 웹 앱만
    python usecase_execution_rate.py JPetStore2 PetClinic -o ./out
"""
from usecase_matrix_common import run


def execution_rate(executed: int, total: int) -> float:
    return executed / total if total else 0.0


if __name__ == '__main__':
    run('컴포넌트별 유스케이스 실행 비율 행렬 생성', 'UsecaseExecutionRate', execution_rate)
