# 사진 압축기

PNG, JPG, BMP, WebP, TIFF 등 각종 이미지 파일을 간편하게 압축하는 Windows 데스크탑 프로그램입니다.

## 주요 기능

- **다양한 포맷 지원**: PNG, JPG/JPEG, BMP, WebP, TIFF/TIF
- **3단계 압축 수준**: 극한(최대 압축) / 권장(균형) / 저압축(화질 우선)
- **출력 형식 선택**: JPEG로 변환 (권장) / WebP로 변환 / 원본 형식 유지
- **최대 크기 제한**: 가로/세로 최대 픽셀 수 지정 (선택사항)
- **드래그 앤 드롭**: 파일을 창에 바로 드래그하여 추가
- **배치 처리**: 여러 파일을 한 번에 압축
- **원본 보존**: 원본 파일은 절대 수정하지 않음
- **결과 자동 저장**: `바탕화면/이미지압축결과` 폴더에 저장

## 사용 방법

### 실행 파일 (.exe) 사용 — 가장 간단

1. [Releases](../../releases) 페이지에서 `사진압축기.exe` 다운로드
2. 더블클릭으로 실행 (Python 설치 불필요)

### 소스코드로 실행

**요구사항**: Python 3.10 이상

```bash
pip install -r requirements.txt
python app.py
```

또는 `run.bat` 더블클릭

## 압축 수준 안내

| 수준 | JPEG 품질 | 특징 |
|------|-----------|------|
| 극한 | 45% | 파일 크기 최소화, 화질 손상 있음 |
| 권장 | 72% | 크기와 화질의 균형 (기본값) |
| 저압축 | 85% | 화질 우선, 압축률 낮음 |

## 출력 형식 안내

| 형식 | 설명 |
|------|------|
| **JPEG로 변환** (권장) | 압축률이 가장 좋음. PNG/BMP 등도 모두 JPEG로 변환 |
| WebP로 변환 | 최신 포맷, 좋은 압축률. 구형 프로그램 호환성 낮음 |
| 원본 형식 유지 | 원본과 같은 포맷으로 저장 (BMP는 예외적으로 JPEG 변환) |

## 빌드 방법

단일 실행 파일(.exe)로 빌드:

```bash
build.bat
```

빌드 완료 후 `dist/사진압축기.exe` 생성

**요구사항**: Python 3.10 이상, PyInstaller

```bash
pip install pyinstaller pillow tkinterdnd2
```

## 프로젝트 구조

```
사진압축/
├── app.py              # 진입점
├── requirements.txt    # 의존성
├── 사진압축기.spec     # PyInstaller 빌드 설정
├── build.bat           # 빌드 스크립트
├── run.bat             # 개발용 실행 스크립트
├── core/
│   ├── compressor.py   # 압축 엔진 (Pillow 기반)
│   └── utils.py        # 유틸리티 함수
└── ui/
    └── main_window.py  # tkinter UI
```

## 기술 스택

- **UI**: Python tkinter + tkinterdnd2 (드래그앤드롭)
- **압축**: [Pillow](https://python-pillow.org/) (PIL)
- **빌드**: PyInstaller (단일 .exe)
