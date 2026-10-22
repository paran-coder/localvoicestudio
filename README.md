# Local Voice Studio — GitHub / Vercel bundle v1.0.0

이 폴더 내용 전체를 GitHub 저장소 루트에 업로드한다. Vercel에서 해당 repo를 Import: Framework Other, vercel.json의 빌드와public출력사용. GitHub 업로드/실제Vercel 배포는 아직 하지 않았다.

- index.html: 소개·다운로드페이지. OG/Twitter태그 포함. 실제 더빙 UI는Windows앱에서 실행.
- og-image.png: AI생성 OG공유이미지, 실제 크기는 이미지태그 참조.
- downloads/: 사용자실행용 ZIP(소스와설치준비스크립트만,모델미포함).
- 2026-10-22-windows-source/: ZIP과동일한Windows배포소스.
- 2026-10-22-build.mjs: Vercel에서public생성.

SITE_URL을 https://실제도메인 으로 설정하는것을 권장. 미설정시 VERCEL_PROJECT_PRODUCTION_URL,그다음 VERCEL_URL에서절대URL구성. 커스텀도메인변경시SITE_URL수정후재배포. 원본 index.html의__SITE_URL__은 빌드에서 치환된다. public산출물만배포한다. 로컬빌드 PowerShell: $env:SITE_URL='http://localhost:8787'; node 2026-10-22-build.mjs

Windows패키지는깨끗한PC전체설치미검증인beta bootstrap. 인증서서명된EXE/MSI가아니며 ZIP압축해제후CMD실행. 현재최종본/모델/사용자결과는포함하지않는다. 원본앱코드의공개라이선스는소유자가지정해야하며 임의MIT등을부여하지않았다.

공유미리보기실제반영은공개배포후확인. 현재라이브URL은미정.
