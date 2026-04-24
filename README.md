# 사진 압축기

PNG, JPG, BMP, WebP, TIFF, HEIC 등 각종 이미지 파일을 간편하게 압축하는 Windows 데스크탑 프로그램입니다.

PyQt6 기반의 따뜻한 베이지/테라코타 디자인 UI, 드래그 앤 드롭, 배치 처리, 자동 해상도 조정을 지원합니다.

## 주요 기능

- **다양한 포맷 지원**: PNG, JPG/JPEG, BMP, WebP, TIFF/TIF, **HEIC/HEIF** (iPhone 사진)
- **3단계 압축 수준**: 최대 압축 / 권장 / 저압축
- **출력 형식 선택**: JPEG (권장) / WebP / 원본 형식 유지
- **최대 크기 제한**: 가로/세로 최대 픽셀 수 지정 (선택)
- **드래그 앤 드롭**: 파일을 창에 바로 드래그하여 추가
- **배치 처리**: 여러 파일을 한 번에 압축
- **HEIC 자동 리사이즈**: HEVC 대비 JPEG 효율 보정을 위해 압축 수준별 자동 해상도 조정
- **EXIF 메타데이터 제거** (선택 수준) · **자동 흑백 감지** (JPEG 용량 ≈ 2× 절감)
- **oxipng 후처리**: PNG 무손실 추가 최적화
- **원본 보존**: 원본 파일은 절대 수정하지 않음
- **결과 자동 저장**: `바탕화면/이미지압축결과` 폴더에 저장
- **압축 효과 없으면 건너뜀**: 압축 후 크기가 더 커지면 원본을 그대로 사용

## 사용 방법

### 실행 파일 사용 — 가장 간단

1. [Releases](../../releases) 페이지에서 `사진압축기.zip` 다운로드
2. 원하는 폴더에 압축 해제
3. `사진압축기/사진압축기.exe` 더블클릭으로 실행 (Python 설치 불필요)

> v2.0.1부터는 **onedir** 방식으로 빌드합니다. 단일 .exe(onefile)보다 첫 실행이 훨씬 빠르고, 압축 시 간헐적으로 뜨던 cmd 창도 사라집니다.

### 소스코드로 실행

**요구사항**: Python 3.10 이상

```bash
pip install -r requirements.txt
python app.py
```

또는 `run.bat` 더블클릭

## 압축 수준 안내

| 수준 | JPEG 품질 | HEIC 자동 리사이즈 | 예상 감소율 |
|------|-----------|--------------------|-------------|
| 최대 압축 | Q40 | 1920px | 60–85% |
| 권장       | Q68 | 2560px | 35–65% |
| 저압축     | Q82 | 원본 해상도 유지 | 15–35% |

> HEIC/HEIF 원본은 이미 HEVC 코덱으로 고효율 인코딩되어 있어, 일반 JPEG 재인코딩만으로는 용량이 잘 줄지 않습니다. 따라서 압축 수준별로 자동 해상도/품질 조정을 적용합니다.

## 출력 형식 안내

| 형식 | 설명 |
|------|------|
| **JPEG** (권장) | 압축률이 가장 좋음. PNG/BMP/HEIC 등도 모두 JPEG로 변환 |
| WebP | 최신 포맷, 좋은 압축률. 구형 프로그램 호환성 낮음 |
| 원본 형식 유지 | 원본과 같은 포맷으로 저장 (BMP/HEIC는 예외적으로 JPEG 변환) |

## 빌드 방법

단일 실행 파일(.exe)로 빌드:

```bash
build.bat
```

빌드 완료 후 `dist/사진압축기.exe` 생성

**요구사항**: Python 3.10 이상, PyInstaller

```bash
pip install pyinstaller pillow pillow-heif pyoxipng PyQt6
```

## 프로젝트 구조

```
사진압축/
├── app.py              # PyQt6 진입점
├── requirements.txt    # 의존성
├── 사진압축기.spec     # PyInstaller 빌드 설정
├── build.bat           # 빌드 스크립트
├── run.bat             # 개발용 실행 스크립트
├── core/
│   ├── compressor.py   # 압축 엔진 (Pillow + pillow-heif + oxipng)
│   └── utils.py        # 유틸리티 함수
└── ui/
    ├── styles.py       # QSS 디자인 토큰 · 스타일시트
    └── main_window.py  # PyQt6 UI (프레임리스 · 커스텀 타이틀바)
```

## 기술 스택

- **UI**: PyQt6 (프레임리스 윈도우 + 커스텀 QPainter 위젯 + QSS)
- **압축**:
  - [Pillow](https://python-pillow.org/) — JPEG/PNG/WebP/TIFF/BMP
  - [pillow-heif](https://github.com/bigcat88/pillow_heif) — HEIC/HEIF 디코딩
  - [pyoxipng](https://pypi.org/project/pyoxipng/) — PNG 무손실 추가 최적화
- **빌드**: PyInstaller (단일 .exe)
