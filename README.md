# Photo Normalizer

상품 이미지를 일괄 보정해서 일관된 `1000x1000` 결과물로 만드는 CLI입니다.

## 요구 사항

- Python 3.11+
- `uv`
- ImageMagick 7 (`magick` 명령 사용 가능)

## 설치

```bash
uv sync --extra dev
```

설치 확인:

```bash
uv run python normalize.py --help
magick --version
```

## 기본 사용법

입력 폴더 안의 이미지를 처리하면 기본적으로 `normalized/` 하위 폴더에 결과가 생성됩니다.

```bash
uv run python normalize.py ./images
```

예시 출력:

```text
Input:  /path/to/images
Output: /path/to/images/normalized
Config: /path/to/config.yaml

Done: 10 processed, 0 skipped

Report:  /path/to/images/normalized/_report.json
Preview: /path/to/images/normalized/_preview.html
```

## 출력 위치 변경

```bash
uv run python normalize.py ./images --output ./out
```

## 드라이런

이미지 파일은 만들지 않고 리포트만 생성합니다.

```bash
uv run python normalize.py ./images --dry-run --output ./dry-run
```

드라이런 결과:

- `_report.json` 생성
- 보정 이미지 미생성
- `_preview.html` 미생성

## 설정 파일

기본 설정은 프로젝트 루트의 [`config.yaml`](./config.yaml)을 사용합니다.

다른 설정 파일을 지정하려면:

```bash
uv run python normalize.py ./images --config ./my-config.yaml
```

입력 폴더 안에 `config.yaml`이 있으면 그 파일이 우선 사용됩니다.

## 자주 쓰는 옵션

```bash
uv run python normalize.py ./images \
  --target-ratio 0.75 \
  --no-angle \
  --morphology \
  --morph-kernel 5 \
  --fuzz 5%
```

- `--output`: 결과 폴더 지정
- `--config`: 사용할 설정 파일 지정
- `--target-ratio`: 피사체가 캔버스에서 차지하는 목표 비율 덮어쓰기
- `--fuzz`: trim fuzz 값 덮어쓰기
- `--no-angle`: 각도 보정 비활성화
- `--morphology`: morphology 처리 활성화
- `--morph-kernel`: morphology kernel 크기 지정
- `--dry-run`: 파일 저장 없이 리포트만 생성

## 입력 파일 형식

다음 확장자를 처리합니다.

- `.jpg`
- `.jpeg`
- `.png`
- `.tif`
- `.tiff`

## 생성 결과물

일반 실행 시 출력 폴더에는 다음 파일이 생성됩니다.

- 보정된 이미지 파일들
- `_report.json`
- `_preview.html`

`_preview.html`에는 다음 화면이 포함됩니다.

- 결과물 격자
- Before/After 비교
- 보정 수치 테이블
