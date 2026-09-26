# WRRA Game 1.0 재현 패키지

## 기본 정보

- 한국어 제목: **복잡게임의 최소 충분상태와 실제 바둑 엔진**
- English title: **WRRA Game 1.0: Minimal Sufficient State, Exhaustive Validation, and a Playable Go Engine**
- Subtitle: **From Omok and Go State Analysis to WRRA Go 0.1**
- 저자: Wonsik Choi · 최원식
- 연락처: janefather@gmail.com
- 버전: 1.0
- 공개일: 2026-09-17
- 관련 연구: WRRA Core 1.0, DOI 10.5281/zenodo.22650956

## 무엇을 합쳤는가

이 배포본은 이전의 Game 연구를 세 단계의 한 계보로 통합한다.

1. **WRRA Game 0.1 — 구성적 사례**  
   9×9 자유형 오목의 특정 상태에서 중앙 한 수가 네 개의 다음 수 승리 출구를 만들며, 뒤따르는 70개 합법 방어 가운데 네 출구를 모두 지우는 수가 없음을 계산했다. 5×5 단순 패 사례에서는 같은 현재 판이라도 직전 판 residue에 따라 되따내기의 합법성이 달라짐을 구성했다.
2. **WRRA Game 0.2 — 전수검증**  
   4×4 3목 Connect K의 도달상태 6,036,001개에서 인증된 Renderer 후보축약의 minimax 값 불일치가 0개임을 확인했다. 3×3 단순 패 바둑의 도달상태 132,161개와 합법전이 420,710개를 열거해, 같은 판·차례·패스 수를 공유하면서 residue 때문에 합법수 집합이 달라지는 가시상태 동치류 752개를 찾았다.
3. **WRRA Game 1.0 / WRRA Go 0.1 — 실제 행위자**  
   위 상태·전이 구조를 실제 바둑 엔진에 넣었다. 엔진은 포획, 자살수 금지, 단순 패, 패스, 두 패스 종료, area score를 실행하고, 11개 투명 Renderer 채널과 MCTS를 결합해 수를 선택한다. 후보별 방문 수·평균가치·prior·Renderer 점수·phenotype을 JSON Ledger에 남긴다.

## 용어 정정 — ‘미래 예측’이 아니다

이 배포본에서는 오해를 부르는 **“미래를 보존한다”**, **“미래를 예측한다”**라는 표현을 연구 명제로 사용하지 않는다.

- residue는 미래 자체를 저장하지 않는다. **현재 판만으로 판정할 수 없는 합법수 제약을 현재 상태에 포함하여, 합법수 집합과 다음 상태의 갱신 규칙을 정확히 만든다.**
- 탐색은 이미 존재하는 미래를 알아내는 과정이 아니다. **현재 규칙이 허용하는 후속 상태를 생성하고 목적값에 따라 비교하는 계산이다.**
- 초기 0.1 연구에서 사용된 “미래 전이집합”이라는 역사적 표현은 이 배포본에서 **“다음 합법 전이집합”**으로 해석하고 통일했다.

## 이번 실행의 핵심 결과

| 검증 | 조건 | 결과 |
|---|---|---|
| 결정적 규칙검사 | 포획·자살수·단순 패·두 패스·좌표·열린 영역 오인 방지 등 | 10/10 PASS |
| 5×5 대조 대국 | WRRA MCTS 대 균등 MCTS, 양쪽 모두 수당 48 simulations, 색상 교대 | 15승 1패, 93.75% |
| 5×5 대조 대국 | WRRA MCTS 대 무작위 합법수, 색상 교대 | 16승 0패 |
| 9×9 자기대국 | 양쪽 수당 24 simulations, komi 5.5 | 82수, 두 패스 종료, 백 8.5집 승 |

이 수치는 전문 바둑엔진의 기력에 관한 주장이 아니다. 같은 유한 규칙과 통제된 계산량에서 WRRA의 충분상태·Renderer·탐색·Ledger가 하나의 실행 가능한 의사결정계로 연결되는지를 확인한 결과다.

## 파일 구성

```text
WRRA_Game_1.0_Zenodo/
├── README_KR.md
├── CITATION.cff
├── SHA256SUMS.txt
├── requirements.txt
├── report/
│   ├── WRRA_Game_1.0_...docx
│   └── WRRA_Game_1.0_...pdf
├── src/
│   ├── wrra_game_0_1.py
│   ├── wrra_game_0_2.py
│   └── wrra_go_0_1.py
└── data/
    ├── wrra_game_0_1_results.json
    ├── wrra_game_0_2_results.json
    ├── wrra_go_0_1_rule_tests.json
    ├── wrra_go_0_1_benchmark.json
    ├── wrra_go_0_1_selfplay_9x9.json
    └── wrra_go_0_1_selfplay_9x9.sgf
```

## 재현 명령

압축을 푼 디렉터리에서 다음을 실행한다.

```bash
python -m pip install -r requirements.txt
python src/wrra_game_0_1.py --output-dir data/reproduced_game_0_1
python src/wrra_go_0_1.py test --output data/reproduced_rule_tests.json
python src/wrra_game_0_2.py --output data/reproduced_game_0_2_results.json
python src/wrra_go_0_1.py benchmark --size 5 --paired-games 8 --simulations 48 --komi 2.5 --seed 20260917 --output data/reproduced_benchmark.json
python src/wrra_go_0_1.py selfplay --size 9 --simulations 24 --komi 5.5 --seed 20260917 --output data/reproduced_selfplay_9x9.json
python src/wrra_go_0_1.py play --size 9 --human B
```

Game 0.2 전수검증과 9×9 자기대국은 환경에 따라 시간이 걸린다. WRRA Go 0.1과 Game 0.2는 Python 표준 라이브러리만 사용하며, Game 0.1의 그림 생성에만 `matplotlib`가 필요하다.

무결성 확인:

```bash
sha256sum -c SHA256SUMS.txt
```

## Zenodo 입력 권장안

- **Title:** WRRA Game 1.0: Minimal Sufficient State, Exhaustive Validation, and a Playable Go Engine
- **Subtitle:** From Omok and Go State Analysis to WRRA Go 0.1
- **Resource type:** Software
- **Creator:** Wonsik Choi
- **Contact:** janefather@gmail.com
- **Keywords:** WRRA; Go; Baduk; Omok; Connect K; Monte Carlo Tree Search; MCTS; minimal sufficient state; state sufficiency; residue; renderer; exhaustive search; complex systems; explainable game AI
- **Related identifier:** 10.5281/zenodo.22650956 — is supplemented by this upload

**Description**

> This release integrates the WRRA Game research program from constructive game analysis to exhaustive finite-state validation and a playable Go engine. WRRA Game 0.1 identifies an Omok forced-win phenotype and a simple-ko residue counterexample. WRRA Game 0.2 exhaustively enumerates 6,036,001 reachable Connect-K states and 132,161 reachable 3×3 Go states, finding zero minimax-value mismatches for the certified Renderer reduction and 752 visible-state classes whose legal actions depend on the previous-board residue. WRRA Go 0.1 reuses the verified state-transition system in a playable 9×9 engine, combining an eleven-channel transparent Renderer with Monte Carlo Tree Search. The archive includes source code, machine-readable ledgers, deterministic rule tests, paired-control matches, and an SGF self-play record. The work evaluates rule-permitted continuations; it does not describe residue or search as prediction of a pre-existing future.

## 라이선스

이 배포본은 범위에 따라 두 라이선스를 적용한다.

- `src/`와 `tools/`의 소스 코드는 **MIT License**로 배포한다.
- 보고서, 문서, 그림, 기계 판독 데이터와 SGF 기보는 **Creative Commons Attribution 4.0 International License (CC BY 4.0)**로 배포한다.

정확한 적용 범위와 조건은 [`LICENSE`](LICENSE), [`LICENSE-CODE`](LICENSE-CODE), [`LICENSE-CONTENT`](LICENSE-CONTENT)를 참조한다.
