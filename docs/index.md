# Photo Normalizer

Photo Normalizer는 상품 이미지를 일괄 보정해 일관된 `1000x1000` 결과물로 만드는 Python CLI입니다. 여러 장의 이미지를 한 번에 처리하면서 리포트와 미리보기까지 함께 생성할 수 있어, 반복적인 상세 페이지용 이미지 정리에 적합합니다.

## 무엇을 할 수 있나요?

- 입력 폴더의 상품 이미지를 한 번에 보정
- 기본 출력 경로에 결과 이미지와 리포트 생성
- 설정 파일 또는 CLI 옵션으로 처리 방식 조정
- 드라이런으로 결과 리포트만 먼저 확인

## 요구 사항

- Python 3.11 이상
- `uv`
- ImageMagick 7 (`magick` 명령 사용 가능)

## 설치

개발 환경까지 함께 준비하려면 프로젝트 루트에서 아래 명령을 실행합니다.

```bash
uv sync --extra dev
```

설치 후에는 다음 명령으로 CLI와 외부 의존성이 정상인지 확인할 수 있습니다.

```bash
uv run python normalize.py --help
magick --version
```

## 빠른 시작

입력 폴더를 지정하면 기본적으로 해당 폴더 아래 `normalized/` 디렉터리에 결과가 생성됩니다.

```bash
uv run python normalize.py ./images
```

출력 위치를 직접 지정하려면:

```bash
uv run python normalize.py ./images --output ./out
```

이미지를 실제로 저장하지 않고 처리 결과만 점검하려면 드라이런을 사용할 수 있습니다.

```bash
uv run python normalize.py ./images --dry-run --output ./dry-run
```

설정 파일을 바꿔 실행하려면:

```bash
uv run python normalize.py ./images --config ./my-config.yaml
```

## 자주 사용하는 옵션

```bash
uv run python normalize.py ./images \
  --target-ratio 0.75 \
  --no-angle \
  --morphology \
  --morph-kernel 5 \
  --fuzz 5%
```

- `--output`: 결과 폴더를 직접 지정합니다.
- `--config`: 사용할 설정 파일을 지정합니다.
- `--target-ratio`: 피사체가 캔버스에서 차지하는 목표 비율을 덮어씁니다.
- `--fuzz`: trim fuzz 값을 조정합니다.
- `--no-angle`: 각도 보정을 비활성화합니다.
- `--morphology`: morphology 처리를 활성화합니다.
- `--morph-kernel`: morphology kernel 크기를 지정합니다.
- `--dry-run`: 이미지 저장 없이 리포트만 생성합니다.

## 생성 결과물

일반 실행 시 출력 폴더에는 다음 결과물이 생성됩니다.

- 보정된 이미지 파일들
- `_report.json`
- `_preview.html`

자세한 옵션과 인자 설명은 `CLI 레퍼런스` 문서를 참고하세요.
