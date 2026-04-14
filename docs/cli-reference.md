# CLI 레퍼런스

## 기본 형식

```
uv run python normalize.py <입력폴더> [옵션...]
```

---

## 명령어 목록

### 1. 기본 실행

```bash
uv run python normalize.py ./images
```

`./images` 폴더 안의 이미지(`.jpg` `.jpeg` `.png` `.tif` `.tiff`)를 모두 처리해서 `./images/normalized/` 에 결과를 저장합니다.

**실행 흐름 (파이프라인 5단계)**

| 단계 | 내용 |
|------|------|
| Step 0 | 색상 정규화 — sRGB 변환, ICC 프로파일 적용, EXIF 제거 |
| Step 1 | 피사체 검출 — bounding box, 기울기 각도, 배경 밝기 측정 |
| Step 2 | 각도 보정 — 배치 내 중앙값 기준으로 기울어진 이미지 회전 |
| Step 3 | 크롭 & 리사이즈 — 피사체 중심 기준 크롭 후 1000×1000으로 확장 |
| Step 4 | 밝기 보정 — 배치 내 중앙값 기준으로 배경 밝기 균일화 |
| Step 5 | 마무리 — 흰색 캔버스(1000×1000)에 배치, ICC 프로파일 삽입 |

**터미널 출력**

```
Input:  /path/to/images
Output: /path/to/images/normalized
Config: /path/to/config.yaml

Done: 10 processed, 0 skipped

Report:  /path/to/images/normalized/_report.json
Preview: /path/to/images/normalized/_preview.html
```

처리에 실패한 이미지는 `SKIP <파일명>: <오류 메시지>` 형태로 출력됩니다.

**생성 파일**

```
images/normalized/
├── product_01.jpg        # 보정된 이미지
├── product_02.jpg
├── ...
├── _report.json          # 보정 수치 리포트
└── _preview.html         # Before/After 미리보기
```

> 출력 폴더가 이미 존재하고 비어 있지 않으면 실행이 중단됩니다. 매 실행 전에 기존 결과물을 지우거나 `--output` 으로 새 폴더를 지정하세요.

---

### 2. 출력 폴더 지정 `--output`

```bash
uv run python normalize.py ./images --output ./out
```

결과를 `./images/normalized` 대신 지정한 경로에 저장합니다.  
입력 폴더와 동일한 경로는 허용되지 않습니다.

---

### 3. 드라이런 `--dry-run`

```bash
uv run python normalize.py ./images --dry-run --output ./dry-run
```

이미지 파일을 생성하지 않고 `_report.json` 만 저장합니다. 보정 수치를 미리 확인하거나 설정을 검증할 때 사용합니다.

**터미널 출력**

```
Input:  /path/to/images
Output: /path/to/dry-run
Config: /path/to/config.yaml
Mode:   dry-run

Done: 10 processed, 0 skipped

Report:  /path/to/dry-run/_report.json
```

**생성 파일**

```
dry-run/
└── _report.json    # 보정 수치만 기록, _preview.html 없음
```

---

### 4. 설정 파일 지정 `--config`

```bash
uv run python normalize.py ./images --config ./my-config.yaml
```

기본 `config.yaml` 대신 지정한 설정 파일을 사용합니다.

**설정 파일 우선순위**

1. `--config` 로 명시적으로 지정한 파일
2. 입력 폴더(`./images/config.yaml`) 안에 있는 파일
3. 프로젝트 루트의 `config.yaml`
4. 코드 내장 기본값

---

### 5. 피사체 비율 지정 `--target-ratio`

```bash
uv run python normalize.py ./images --target-ratio 0.75
```

피사체가 캔버스(1000×1000)에서 차지하는 목표 비율을 덮어씁니다.  
기본값은 `config.yaml`의 `framing.target_ratio` (기본 `0.80`).

| 값 | 결과 |
|----|------|
| `0.90` | 피사체가 캔버스를 꽉 채움 |
| `0.80` | 기본값, 사방에 적당한 여백 |
| `0.60` | 피사체가 작게, 여백이 넓게 |

---

### 6. Trim fuzz 지정 `--fuzz`

```bash
uv run python normalize.py ./images --fuzz 5%
```

피사체 검출 시 배경 색상 허용 오차를 덮어씁니다.  
기본값은 `config.yaml`의 `trim.fuzz` (기본 `10%`).

값이 작을수록 배경과 피사체의 경계를 엄격하게 구분합니다. 배경이 단순한 흰색인 경우 `5%` 이하, 그라데이션이나 그림자가 있으면 `15%` 이상을 시도해 보세요.

---

### 7. 각도 보정 비활성화 `--no-angle`

```bash
uv run python normalize.py ./images --no-angle
```

Step 2(각도 보정)를 건너뜁니다. 이미 수직으로 촬영된 이미지이거나 보정이 오히려 품질을 해치는 경우에 사용합니다.

---

### 8. Morphology 처리 `--morphology` / `--morph-kernel`

```bash
uv run python normalize.py ./images --morphology
uv run python normalize.py ./images --morphology --morph-kernel 5
```

피사체 검출 전에 morphology open 처리를 적용해 배경 노이즈를 제거합니다.  
배경에 잡티, 그림자, 반사가 있어서 피사체 검출이 불안정할 때 사용합니다.

`--morph-kernel`은 kernel 크기(픽셀)를 지정합니다. 기본값 `3`. 값이 클수록 노이즈 제거가 강해지지만 피사체 가장자리 정밀도가 낮아집니다.

---

### 9. 옵션 조합 예시

```bash
# 드라이런으로 결과 수치 미리 확인
uv run python normalize.py ./images --dry-run --output ./dry-run

# 여백을 줄이고 각도 보정 없이 처리
uv run python normalize.py ./images \
  --target-ratio 0.90 \
  --no-angle \
  --output ./out

# 배경 노이즈가 많을 때
uv run python normalize.py ./images \
  --morphology \
  --morph-kernel 5 \
  --fuzz 15% \
  --output ./out

# 커스텀 설정 파일 + 결과 폴더 지정
uv run python normalize.py ./images \
  --config ./studio-config.yaml \
  --output ./studio-out
```

---

## 출력 파일 상세

### `_report.json`

배치 전체의 기준값과 파일별 보정 수치를 기록합니다.

```json
{
  "config": { ... },           // 실행에 사용된 설정 전체
  "reference": {
    "brightness_mean": 243.5,  // 배치 전체의 배경 밝기 중앙값
    "angle": -0.42             // 배치 전체의 기울기 중앙값 (도)
  },
  "files": {
    "product_01.jpg": {
      "original_bbox": [x, y, w, h],      // 검출된 피사체 bounding box
      "original_angle": -1.2,             // 원본 기울기 각도
      "original_brightness_mean": 241.3,  // 원본 배경 밝기 평균
      "angle_delta": -0.78,               // 적용된 회전 각도
      "angle_corrected": true,            // 실제로 회전이 수행됐는지 여부
      "corrected_bbox": [x, y, w, h],     // 회전 후 재검출된 bounding box
      "crop_applied": [x, y, w, h],       // 실제 크롭 영역
      "resize_scale": 1.12,               // 리사이즈 배율
      "brightness_delta": 2.2,            // 적용된 밝기 보정량
      "warnings": []                      // 경고 메시지 (예: 과도한 업스케일)
    },
    "product_02.jpg": {
      ...
      "error": "STEP 1 error: no subject detected"  // 처리 실패 시 오류 메시지
    }
  }
}
```

`warnings` 에는 `resize_scale`이 `max_upscale`(기본 `1.3`)을 초과할 때 경고가 기록됩니다.

### `_preview.html`

브라우저에서 열면 다음 화면이 포함됩니다.

- **결과물 격자** — 보정된 이미지 전체를 한눈에 확인
- **Before/After 비교** — 원본과 보정본 나란히 비교
- **보정 수치 테이블** — 파일별 각도·밝기·크롭 수치 일람

드라이런(`--dry-run`)에서는 생성되지 않습니다.

---

## config.yaml 설정 항목

```yaml
canvas:
  width: 1000         # 출력 이미지 가로 크기 (px)
  height: 1000        # 출력 이미지 세로 크기 (px)
  background: "#FFFFFF"  # 배경 색상

color_management:
  srgb_convert: true  # sRGB 색공간 변환 여부
  icc_profile: "assets/profiles/sRGB_IEC61966-2-1.icc"
  strip_exif: true    # EXIF 메타데이터 제거 여부
  preserve_icc: true  # ICC 프로파일 유지 여부

framing:
  target_ratio: 0.80  # 피사체가 캔버스를 차지하는 목표 비율 (0~1)
  max_upscale: 1.3    # 최대 업스케일 배율 (초과 시 warnings에 기록)

brightness:
  method: "level"           # 밝기 보정 방식: "level" 또는 "brightness-contrast"
  reference: "median"       # 기준값 산출 방식 (현재 "median" 고정)
  target: "background"      # 보정 대상 (현재 "background" 고정)
  corner_sample_size: 100   # 배경 밝기 측정에 사용할 모서리 영역 크기 (px)

angle:
  enabled: true       # 각도 보정 활성화 여부
  reference: "median" # 기준 각도 산출 방식 (현재 "median" 고정)
  tolerance: 2.0      # 이 값(도) 이하 차이는 보정 안 함

morphology:
  enabled: false      # morphology 처리 활성화 여부
  operation: "open"   # 처리 방식: open / close / erode / dilate
  kernel_size: 3      # kernel 크기 (px)

trim:
  fuzz: "10%"         # 배경 색상 허용 오차
```
