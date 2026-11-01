# Info
서버에 저장된 JPetStore6의 실행 트레이스로는 현재의 행동 모델을 재현하기 위한 컴포넌트별 시나리오 실행 여부 행렬을 생성할 수 없음.
따라서 Traces 폴더에서 JPetStore6는 제외되었음.

DayTrader는 재실험을 하는 과정에서 AOP를 손봤고 조금 더 잘 다룰 때여서 이미 Include 관계가 고려되어 있기에 Includes 폴더에 DayTrader는 제외되었음.

# Include 관계
현재 Traces 폴더의 모든 웹 앱(JPetStore2, PetClinic, ShoppingApp, DayTrader) 트레이스에는 Include 관계가 이미 삽입되어 있음.
행렬 생성 스크립트는 Include 관계를 따로 처리하지 않고 트레이스 내용만 사용함.

새 트레이스를 추가했다면 행렬을 만들기 전에 `insert_includes.py`를 먼저 실행해야 함. 실행하지 않아도 경고 없이 Include 대상 컴포넌트만 빠진 행렬이 만들어짐.

# 사용법
JPetStore6는 트레이스가 없어 실행할 수 없으므로, 웹 앱을 생략하지 말고 지정해서 실행함.

```
python insert_includes.py <webapp>          # 트레이스 전처리 (필요할 때만, 원본 트레이스가 변경됨)
python components_by_scenario.py <webapp>   # ComponentsByScenarios: 시나리오별 컴포넌트 실행 여부
python usecase_participation.py <webapp>    # UsecaseParticipation: 유스케이스별 컴포넌트 실행 여부
python usecase_execution_rate.py <webapp>   # UsecaseExecutionRate: 유스케이스별 컴포넌트 실행 비율
```

`insert_includes.py`는 이미 있는 컴포넌트를 다시 넣지 않으므로 여러 번 실행해도 결과가 같음. `Includes/<webapp>.xlsx`와 트레이스가 모두 있는 웹 앱(JPetStore2, PetClinic, ShoppingApp)에만 실행할 수 있음.
