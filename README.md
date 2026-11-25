# GitGen (Codyssey-B3-2)

> **Git 변경 사항(`git status`, `git diff`)을 분석하여 의미 있는 커밋 메시지와 Pull Request 설명을 자동으로 생성하는 CLI 도구**

`gitgen`은 Git 변경 맥락을 수집하고 AI 프롬프트를 통해 팀 표준에 부합하는 커밋 메시지와 PR 초안을 단 1회의 REST API 호출로 생성합니다.  
특정 벤더 SDK에 종속되지 않는 순수 Python 표준 라이브러리(Zero-dependency) 기반 REST 클라이언트로 구현되어 있어, **Google Gemini**, **OpenAI**, **Anthropic Claude**, 그리고 **사용자 정의 OpenAI 호환 엔드포인트(Ollama, Groq, DeepSeek 등)**를 범용 `AI_API_KEY` 하나로 유연하게 지원합니다.

---

## 목차
1. [주요 특징](#주요-특징)
2. [프로젝트 아키텍처](#프로젝트-아키텍처)
3. [설치 및 요구 사항](#설치-및-요구-사항)
4. [환경변수 설정](#환경변수-설정)
5. [사용법 및 CLI 옵션](#사용법-및-cli-옵션)
6. [실행 결과 예시](#실행-결과-예시)
7. [보안 및 안전 모드 (Safe Mode)](#보안-및-안전-모드-safe-mode)
8. [비용 최적화 및 운영 가이드](#비용-최적화-및-운영-가이드)
9. [팀 컨벤션 커스터마이징](#팀-컨벤션-커스터마이징)
10. [테스트 실행](#테스트-실행)

---

## 주요 특징

- **REST API 직접 연동 (Zero External Dependencies)**: 별도의 무거운 외부 패키지(`requests`, vendor SDK 등) 설치 없이 Python 3.10+ 표준 라이브러리(`urllib.request`, `json`)만으로 REST 통신을 수행합니다.
- **멀티 프로바이더 지원**: `AI_API_KEY` 환경변수 또는 `--provider` / `--model` 옵션을 통해 Gemini, OpenAI, Claude, 로컬 LLM을 자동 감지하고 요청 페이로드를 변환합니다.
- **철저한 형식 및 길이 검증**:
  - 커밋 제목: 50자 권장, 최대 72자 제한 및 필수 타입 prefix 보장
  - 커밋 본문: 핵심 변경 사항 1~3개 불릿 포인트 및 변경 파일 언급 보장
  - PR 제목: 최대 80자 1줄 출력
  - PR 본문: `## Why`, `## What`, `## How to Test` 템플릿 헤더 및 섹션별 1개 이상 불릿 포인트 필수 보장
- **단 1회 호출 기반 후처리(Post-processing) 아키텍처**: API 재호출로 인한 토큰 낭비와 비용 발생을 원천 차단하기 위해, 출력 형식 검증 및 다듬기 작업을 파이썬 후처리 엔진에서 즉시 처리합니다.
- **안전 모드 (`--safe-mode`) 탑재**: `git diff` 내 API Key, 토큰, 비밀번호, 이메일, 개인정보를 정규식 기반으로 자동 마스킹하고, 대량 변경 시 diff 파일 및 줄 수를 안전하게 제한합니다.

---

## 프로젝트 아키텍처

```
Codyssey-B3-2/
├── gitgen/                     # 핵심 도메인 로직 패키지
│   ├── __init__.py
│   ├── git_service.py          # Git 변경 사항 수집 (branch, status, diff)
│   ├── safe_mode.py            # 민감정보 정규식 마스킹 및 diff 길이 제한
│   ├── prompt_builder.py       # Commit/PR 프롬프트 템플릿 생성
│   ├── validator.py            # 길이/형식 검증 및 후처리(Post-processing)
│   ├── convention.py           # .ai-gitgen.yml 컨벤션 설정 파서
│   └── providers/              # REST API AI 프로바이더
│       ├── __init__.py
│       ├── base.py             # BaseProvider 추상 클래스 및 HTTP 공통 처리
│       ├── gemini.py           # Google Gemini REST v1beta 클라이언트
│       ├── openai.py           # OpenAI 및 OpenAI-compatible REST 클라이언트
│       ├── anthropic.py        # Anthropic Claude REST v1 클라이언트
│       └── factory.py          # 프로바이더 자동 감지 및 팩토리
├── tests/                      # 단위 및 통합 테스트 모음
│   ├── test_git_service.py
│   ├── test_safe_mode.py
│   ├── test_validator.py
│   ├── test_providers.py
│   └── test_cli.py
├── .ai-gitgen.yml.example      # 팀 컨벤션 설정 예시 파일
├── .env.example                # API KEY 환경 변수 예시 파일
├── main.py                     # CLI 실행 진입점 (commit, pr)
└── README.md                   # 사용자 및 운영 가이드
```

### 관심사 분리(Separation of Concerns) 설계 이유
1. **Git 수집(`git_service`)과 AI 통신(`providers`)의 분리**: Git 명령어 변경이나 환경(CI/CD, 로컬 등) 변경 시 AI 호출부와 무관하게 독립적으로 단위 테스트가 가능합니다.
2. **프롬프트 구성(`prompt_builder`)과 검증/포맷팅(`validator`)의 분리**: AI 모델이 생성한 원시 텍스트를 후처리 엔진에서 독립적으로 파싱/정제함으로써 모델의 비결정적 출력(Markdown fence 포함 등)을 안전하게 규격화합니다.
3. **프로바이더 팩토리(`providers/factory`)**: 단일 인터페이스(`generate()`)를 통해 추후 새로운 LLM(Ollama, Groq, Mistral 등) 추가 시 기존 코드를 수정하지 않고 확장(OCP)할 수 있습니다.

---

## 설치 및 요구 사항

- **Python 3.10 이상** (Windows, macOS, Linux 지원)
- **Git** (시스템 PATH에 등록되어 있어야 함)
- 외부 의존성(라이브러리) 설치 불필요 (표준 라이브러리 사용)

저장소를 클론한 후 프로젝트 루트에서 바로 실행할 수 있습니다:
```bash
git clone https://github.com/your-username/Codyssey-B3-2.git
cd Codyssey-B3-2
```

---

## 환경변수 설정

보안을 위해 API Key는 코드에 하드코딩하지 않고 환경변수 또는 `.env` 파일로 관리합니다. 범용 `AI_API_KEY`를 설정하면 시스템이 키 패턴 또는 지정된 모델을 바탕으로 최적의 프로바이더를 자동 감지합니다.

### 방법 1. `.env` 파일 사용 (권장)
프로젝트 루트의 `.env.example` 파일을 복사하여 `.env` 파일을 생성하고 발급받은 가상 키(Virtual Key)를 입력합니다:

```bash
# 템플릿 복사
cp .env.example .env
# Windows PowerShell:
# Copy-Item .env.example .env
```

생성된 `.env` 파일 내용:
```env
# Codyssey 제휴 서드파티 프로바이더 (기본값: copa.codyssey.kr / gpt-5-mini)
AI_API_KEY=sk-cody-live-...

# 또는 직접 제공자 키 사용 시:
# AI_API_KEY=AIzaSyYourGeminiApiKeyHere...
# AI_API_KEY=sk-proj-YourOpenAiKeyHere...
```
> **참고**: `.env` 파일은 `.gitignore`에 등록되어 있어 실수로 원격 저장소에 커밋되지 않도록 안전하게 보호됩니다.

### 방법 2. 셸 환경변수 직접 설정 (세션 일시 주입)

#### Linux / macOS (Bash, Zsh)
```bash
# Codyssey 가상 키 사용 시 (기본 엔드포인트 https://copa.codyssey.kr/v1 자동 적용)
export AI_API_KEY="sk-cody-live-..."

# 또는 Google Gemini / OpenAI를 직접 사용할 경우
export AI_API_KEY="AIzaSy..."
# export AI_API_KEY="sk-proj-..."
```

#### Windows PowerShell
```powershell
# Codyssey 가상 키 사용 시
$env:AI_API_KEY="sk-cody-live-..."

# 또는 Google Gemini / OpenAI 직접 사용 시
$env:AI_API_KEY="AIzaSy..."
```

#### Windows CMD
```cmd
set AI_API_KEY="YOUR_KEY_HERE"
```

> **참고**: 프로바이더별 전용 환경변수인 `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`가 이미 설정되어 있다면 자동으로 대체 감지하여 사용합니다.

---

## 사용법 및 CLI 옵션

### 기본 실행
```bash
# 1. 커밋 메시지 자동 생성
python main.py commit

# 2. PR 제목 및 본문 초안 자동 생성
python main.py pr
```

### 주요 CLI 옵션

| 옵션 | 설명 | 기본값 | 예시 |
| :--- | :--- | :--- | :--- |
| `-m`, `--model` | 사용할 AI 모델 지정 | Provider별 최적 모델 | `--model gemini-3-flash`, `--model gpt-5-mini`, `--model claude-haiku-4` |
| `-p`, `--provider` | AI 제공자 명시 (`gemini`, `openai`, `anthropic`, `custom`) | 키/모델 기반 자동 감지 | `--provider gemini` |
| `-t`, `--temperature` | 생성 다양성 (0.0 ~ 2.0) | `commit`: 0.2, `pr`: 0.3 | `--temperature 0.1` |
| `-k`, `--max-tokens` | 생성될 최대 토큰 수 | `commit`: 300, `pr`: 800 | `--max-tokens 500` |
| `-s`, `--safe-mode` | 민감정보 마스킹 및 diff 길이 제한 활성화 | `False` | `--safe-mode` |
| `--base-url` | 사용자 정의 REST API 엔드포인트 Base URL | 공식 API 엔드포인트 | `--base-url http://localhost:11434/v1` |
| `-c`, `--convention` | 팀 컨벤션 설정 파일 경로 | `.ai-gitgen.yml` (자동 로드) | `--convention my-team-rules.yml` |

> 단일 대시(`-model`, `-safe-mode` 등) 형태의 옵션도 완벽하게 지원합니다.

---

## 실행 결과 예시

### 1. 커밋 메시지 자동 생성 (`python main.py commit`)
```shell
$ python main.py commit
[INFO] Git status 수집 완료: 3개 파일 변경 감지
[INFO] Git diff 수집 완료: 128줄
[INFO] AI API 요청 중... (Provider: gemini, Model: gemini-3-flash)
[DONE] 커밋 메시지 생성 완료
[INFO] AI API 호출 횟수: 1회

--- Commit Message ---
feat: Git 변경 사항 기반 커밋 메시지 자동 생성 기능 추가

- git diff 결과를 수집해 AI 입력 컨텍스트로 전달하도록 구현
- 커밋 메시지 템플릿(feat/fix 등) 생성 규칙 적용
- API Key 미설정 시 안내 메시지 및 에러 처리 개선
----------------------
```

### 2. PR 제목/본문 자동 생성 (`python main.py pr`)
```shell
$ python main.py pr
[INFO] 현재 브랜치: feature/commit-pr-generator
[INFO] Git status 수집 완료: 3개 파일 변경 감지
[INFO] Git diff 수집 완료: 128줄
[INFO] AI API 요청 중... (Provider: gemini, Model: gemini-3-flash)
[DONE] PR 초안 생성 완료
[INFO] AI API 호출 횟수: 1회

--- PR Title ---
feat: 커밋/PR 자동 생성 기능 추가

--- PR Body ---
## Why
- 팀 협업 시 커밋 메시지와 PR 설명 작성에 시간이 소요되어 자동 생성 도구가 필요했습니다.
- Git 변경 사항을 기반으로 일관된 형식의 요약 텍스트를 생성해 리뷰 효율을 높이고자 했습니다.

## What
- git status, git diff 결과를 수집해 AI 입력 컨텍스트로 전달하는 로직 추가
- 커밋 메시지 자동 생성 기능(python main.py commit) 구현
- PR 제목/본문 자동 생성 기능(python main.py pr) 및 템플릿 적용
- API Key 누락/요청 실패 시 에러 메시지 및 예외 처리 개선

## How to Test
- 환경변수 설정: export AI_API_KEY="YOUR_KEY"
- 커밋 메시지 생성: python main.py commit
- PR 초안 생성: python main.py pr
- 결과로 출력된 PR 본문이 Why/What/How to Test 구조와 길이 규칙을 만족하는지 확인
----------------
```

### 3. API Key 미설정 시 에러 예시
```shell
$ python main.py commit
[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.
## 예) export AI_API_KEY="YOUR_KEY"
## (Windows PowerShell: $env:AI_API_KEY="YOUR_KEY")
```

### 4. 변경 사항이 없는 경우 예시
```shell
$ python main.py commit
[INFO] 변경 사항이 없습니다. 커밋 메시지를 생성하지 않고 종료합니다.
```

---

## 보안 및 안전 모드 (Safe Mode)

개발 중 실수로 소스 코드 내에 API Key, 비밀번호, 토큰, 고객 정보 등이 포함된 상태에서 AI 프롬프트로 전송될 위험이 있습니다.  
`--safe-mode` (`-s`) 옵션을 활성화하면 아래의 강력한 보안 정책이 실행됩니다:

### Safe Mode 동작 정책
1. **정규식 기반 민감정보 마스킹**:
   - OpenAI, Gemini, Anthropic, GitHub API 토큰 (`sk-...`, `AIza...`, `ghp_...`)
   - 개인 식별 이메일 주소 (`user@example.com` -> `[REDACTED_EMAIL]`)
   - 소스 코드 내 비밀번호/시크릿 할당 (`password = "secret123"` -> `password: [REDACTED_SECRET]`)
   - Private Key 블록 (`-----BEGIN ... PRIVATE KEY-----` -> `[REDACTED_PRIVATE_KEY]`)
   - Bearer 토큰 및 JWT 토큰
2. **Diff 전송 제한**:
   - 파일 수: 최대 **10개 파일** (초과 시 `...외 N개 파일 생략` 처리)
   - Diff 줄 수: 최대 **200줄** (초과 시 `... [diff truncated by safe-mode: N lines omitted]` 처리)

### Safe Mode ON / OFF 비교
```diff
# 원본 Git Diff (Safe Mode OFF 전송 시):
- api_key = "AIzaSy_SAMPLE_KEY_FOR_DEMONSTRATION"
- db_password = "MySuperSecretPassword2026!"
- admin_email = "lead_developer@company.org"

# Safe Mode ON 적용 후 AI 전송 프롬프트:
- api_key = "[REDACTED_GEMINI_KEY]"
- db_password = [REDACTED_SECRET]
- admin_email = "[REDACTED_EMAIL]"
```

---

## 비용 최적화 및 운영 가이드

### 1. 단 1회 호출 원칙 (Cost Efficiency)
- 본 도구는 실행 1회당 **단 1회의 AI API 호출**을 원칙으로 동작하며, 실행 완료 시 터미널에 `[INFO] AI API 호출 횟수: 1회`를 로깅합니다.
- AI 응답이 규격(커밋 제목 50~72자, PR 3대 헤더 등)을 미세하게 벗어나더라도, 재호출 대신 Python 로컬 `validator` 모듈이 후처리(Post-processing)하여 불필요한 토큰 낭비와 비용을 방지합니다.

### 2. 파라미터 튜닝 가이드
- **`temperature` (생성 다양성)**:
  - 커밋 메시지: `0.1 ~ 0.3` 권장 (결정적이고 일관된 형식 유지)
  - PR 초안: `0.2 ~ 0.4` 권장 (자연스러운 맥락 설명 및 배경 유도)
- **`max_tokens` (최대 생성 토큰)**:
  - 커밋 메시지: `200 ~ 400` 토큰 (제목 1줄 + 핵심 불릿 2~3줄로 충분)
  - PR 본문: `600 ~ 1000` 토큰 (Why, What, How to Test 구조 기술에 적합)

---

## 팀 컨벤션 커스터마이징

팀마다 사용하는 커밋 접두사 규칙이나 PR 템플릿 구조가 다를 수 있습니다.  
프로젝트 루트에 `.ai-gitgen.yml` 파일을 두거나 `--convention` 옵션으로 원하는 규칙을 지정할 수 있습니다.

### 설정 예시 (`.ai-gitgen.yml`)
```yaml
commit_types:
  - feat
  - fix
  - docs
  - style
  - refactor
  - test
  - chore

language: ko
max_commit_title_length: 50
max_pr_title_length: 80

custom_instructions: "커밋 접두사 뒤에 콜론과 공백을 반드시 넣고, 핵심 모듈명을 명시하세요."
```

### 컨벤션 적용 전 / 후 생성 결과 비교
- **컨벤션 적용 전 (기본)**:
  ```
  feat: add authentication logic
  - add token check in auth service
  ```
- **팀 컨벤션 적용 후 (`.ai-gitgen.yml`)**:
  ```
  feat(auth): 사용자 토큰 유효성 검증 로직 구현

  - services/auth.py 모듈에 만료 토큰 핸들러 추가
  - 인증 실패 시 401 Unauthorized 예외 반환 처리
  ```

---

## 테스트 실행

프로젝트에 포함된 단위 및 통합 테스트는 Python 내장 `unittest` 러너로 실행할 수 있습니다:

```bash
# 전체 테스트 실행 (19개 테스트)
python -m unittest discover tests -v
```

모든 핵심 기능(Git context 수집, 정규식 마스킹, diff 자르기, 규격 검증 및 보완, Multi-provider 팩토리, CLI 파이프라인)에 대한 회귀 방지 테스트가 포함되어 있습니다.
