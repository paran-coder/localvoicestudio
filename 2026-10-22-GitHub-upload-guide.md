# GitHub 업로드 · v1.4.0

이 폴더 안의 내용을 저장소 최상위에 올리세요. 상위 프로젝트 전체나 이전 버전 폴더는 올리지 않습니다.

## 포함 구성

- index.html, 2026-10-22-session.js: 웹 편집·엔진 연결 화면
- manual.html, og-image.png: 사용자 매뉴얼·공유 이미지
- downloads/2026-10-22-Local-Voice-Studio-Setup-v1.4.0.exe: 사용자용 설치·복구 프로그램
- 2026-10-22-windows-source/: 내부 엔진 소스
- 2026-10-22-installer.cs, 2026-10-22-build-installer.ps1: 설치기 빌드 소스
- 2026-10-22-build.mjs, vercel.json, .gitignore: Vercel 배포 설정
- README.md, 이 안내: 저장소 설명

Vercel 프로젝트 루트는 저장소 최상위입니다. 빌드·출력 경로는 vercel.json에 지정되어 있습니다. 실제 도메인을 SITE_URL로 지정하거나 Vercel 도메인 자동 감지를 사용하세요.

기존 GitHub 저장소를 갱신한다면 예전 ZIP·설치 EXE와 이전 웹 파일이 배포에 섞이지 않도록 변경 목록을 확인하세요. downloads에는 v1.4.0 EXE 하나만 유지하는 구성입니다. 로컬 보관본을 삭제할 필요는 없습니다.

개인 음성, test, archive, 개발 실행기, 모델, 가상환경, 캐시, 환경 설정, 로그는 업로드 대상이 아닙니다. 현재 폴더에는 포함되어 있지 않습니다.

설치기는 서명되지 않은 베타이며 새 PC 전체 설치·공개 웹 연결 실사용 검증은 별도입니다. GitHub 업로드나 Vercel 배포 자체는 이 정리 작업에서 실행하지 않았습니다.
