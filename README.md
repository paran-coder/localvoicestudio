# Local Voice Studio WEB / local engine v1.1.0

이폴더내용을GitHub저장소루트에업로드. Vercel Other + vercel.json, node 2026-10-22-build.mjs, output public.
index.html=실제편집·더빙화면. manual.html=사용자매뉴얼. og-image.png=공유이미지. downloads=Windows로컬엔진ZIP. windows-source=동일소스.
SITE_URL=https://공개도메인설정권장. 없으면VERCEL_PROJECT_PRODUCTION_URL/VERCEL_URL자동사용. 원본템플릿__SITE_URL__은빌드치환. public/은gitignore대상.
웹:로컬엔진연결확인→트레이코드입력→작업. 엔진http://127.0.0.1:8766, Ollama11435. 첫설치YES동의후Python/패키지/FFmpeg/Ollama/번역모델준비, TTS/STT모델은처음사용시다운로드. 설치후engine-start.vbs로콘솔없이트레이시작.
HTTPS→loopback브라우저권한은지원브라우저에서허용필요. 보안플래그/인증서검증을끄지말것. Origin별세션인증/코드페어링, 파일도인증필요. 토큰은브라우저메모리에만유지.
검증:로컬HTTP웹→실제bridge페어링/무음작업/결과다운로드, CORS·인증거부확인. 미검증:다른PC전체설치,실제tray종합,공개HTTPS브라우저권한/배포,전체TTS. 기존최종앱보존. 새패키지는서명EXE아닌bootstrapZIP.
