"""
Prompt builder for Commit message and Pull Request generation.
"""

from typing import Optional
from gitgen.convention import ConventionConfig
from gitgen.git_service import GitContext


def build_commit_prompt(context: GitContext, convention: Optional[ConventionConfig] = None) -> str:
    """
    Builds a prompt instructing the AI to generate a Git commit message.
    """
    conf = convention or ConventionConfig()
    types_str = ", ".join(conf.commit_types)
    file_list_str = "\n".join(f"- {f}" for f in context.changed_files) if context.changed_files else "(없음)"

    lang_inst = "한국어로 작성하세요." if conf.language == "ko" else "Write in English."

    prompt = f"""당신은 변경된 코드베이스를 분석하여 명확하고 표준적인 Git 커밋 메시지를 작성하는 시니어 소프트웨어 엔지니어입니다.

[Git 변경 컨텍스트]
- 브랜치: {context.branch}
- 변경된 파일 목록 ({context.file_count}개):
{file_list_str}

[Git Diff 내용]
```diff
{context.diff_text}
```

[커밋 메시지 작성 규칙]
1. 제목(Title) 필수 규칙:
   - 형식: <type>: <간결하고 명확한 변경 요약>
   - 유효한 type 목록: [{types_str}]
   - 길이: 50자 이내 권장 (절대 72자를 초과하지 마세요).
   - 명령조/현재형 동사를 사용하고 마침표는 찍지 마세요.
   - {lang_inst}
2. 본문(Body) 규칙:
   - 제목 다음 줄은 반드시 한 줄 띄우세요 (빈 줄 필수).
   - 핵심 변경 사항 1~3개를 불릿 포인트(`- `)로 요약하세요.
   - 본문에 변경된 핵심 파일 또는 모듈 이름을 1~3개 명시하세요.
   - 사소한 오타나 줄바꿈보다는 "무엇을 왜 변경했는지"에 집중하세요.
3. 출력 형식 제약 (매우 중요):
   - 마크다운 코드 블록(```)이나 따옴표를 두르지 마세요.
   - "커밋 메시지 생성 결과:" 같은 설명이나 인사말, 메타 텍스트를 일체 포함하지 마세요.
   - 첫 번째 줄부터 곧바로 커밋 제목으로 시작해야 합니다.
"""

    if conf.custom_instructions:
        prompt += f"\n[추가 팀 컨벤션 요구사항]\n{conf.custom_instructions}\n"

    return prompt.strip()


def build_pr_prompt(context: GitContext, convention: Optional[ConventionConfig] = None) -> str:
    """
    Builds a prompt instructing the AI to generate a Pull Request title and body.
    """
    conf = convention or ConventionConfig()
    types_str = ", ".join(conf.commit_types)
    file_list_str = "\n".join(f"- {f}" for f in context.changed_files) if context.changed_files else "(없음)"

    lang_inst = "한국어로 작성하세요." if conf.language == "ko" else "Write in English."

    prompt = f"""당신은 Git 변경 사항을 검토하여 팀원들이 쉽게 이해할 수 있는 Pull Request(PR) 제목과 본문을 작성하는 시니어 소프트웨어 엔지니어입니다.

[Git 변경 컨텍스트]
- 대상 브랜치: {context.branch}
- 변경된 파일 목록 ({context.file_count}개):
{file_list_str}

[Git Diff 내용]
```diff
{context.diff_text}
```

[PR 제목 및 본문 작성 규칙]
1. PR 제목 (Title) 규칙:
   - 첫 번째 줄에 1줄로 작성 (절대 80자를 초과하지 마세요).
   - 형식: <type>: <핵심 변경 요약> (예: feat: 커밋/PR 자동 생성 기능 추가)
   - 유효한 type 목록: [{types_str}]
   - {lang_inst}
2. PR 본문 (Body) 필수 템플릿 구조:
   - PR 제목 다음 줄은 빈 줄을 두고, 본문은 정확히 아래 3개 헤더 섹션으로 구성해야 합니다:
     ## Why
     - (변경 배경 및 목적: 왜 이 작업이 필요했는지 1~3개 불릿으로 설명)
     
     ## What
     - (핵심 변경 사항: 무엇을 추가/수정/삭제했는지 구체적으로 1~4개 불릿으로 설명)
     
     ## How to Test
     - (테스트 및 검증 방법: 어떻게 실행하고 동작을 확인하는지 1~3개 불릿으로 설명)
   - **각 섹션에는 반드시 1개 이상의 불릿(`- `)이 포함되어야 합니다.**
3. 출력 형식 제약 (매우 중요):
   - 첫 번째 줄은 오직 PR 제목이어야 합니다.
   - 마크다운 코드 블록(```)으로 전체를 감싸지 마세요.
   - 인사말이나 잡담을 일체 포함하지 마세요.
"""

    if conf.custom_instructions:
        prompt += f"\n[추가 팀 컨벤션 요구사항]\n{conf.custom_instructions}\n"

    return prompt.strip()
