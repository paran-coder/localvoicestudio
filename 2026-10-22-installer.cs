using System;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Diagnostics;
using System.Drawing;
using System.Text;
using System.Windows.Forms;
using System.Threading.Tasks;

class Setup : Form {
 const string Version="1.4.0";
 readonly Label status=new Label();readonly TextBox details=new TextBox();readonly Button install=new Button(),repair=new Button(),close=new Button();readonly ProgressBar progress=new ProgressBar();
 readonly string target=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LocalVoiceStudio",Version);
 bool running=false;
 [STAThread] static void Main(string[] args){
  if(args.Length==1&&args[0]=="--verify-payload"){VerifyPayload();return;}
  Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new Setup());
 }
 static void VerifyPayload(){using(var stream=Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))using(var zip=new ZipArchive(stream,ZipArchiveMode.Read)){
  if(zip.Entries.Count<20)throw new Exception("Incomplete payload");foreach(var e in zip.Entries){if(e.FullName.Contains("..")||e.FullName.Contains(":")||e.FullName.Contains("/"))throw new Exception("Invalid entry");using(var s=e.Open()){s.CopyTo(Stream.Null);}}
 }}
 Setup(){
  Text="Local Voice Studio 설치 · 연결 복구";ClientSize=new Size(650,455);MinimumSize=new Size(666,494);StartPosition=FormStartPosition.CenterScreen;Font=new Font("Malgun Gothic",10);BackColor=Color.White;
  var title=new Label{Text="Local Voice Studio",Font=new Font(Font.FontFamily,20,FontStyle.Bold),Location=new Point(28,22),AutoSize=true};Controls.Add(title);
  var description=new Label{Text="설치 환경을 확인하고 웹 스튜디오 연결을 준비합니다.\n기존 Python·모델은 재사용합니다. 명령어를 입력할 필요가 없습니다.",Location=new Point(30,77),Size=new Size(590,52)};Controls.Add(description);
  status.Text="처음 사용하면 설치, 기존 사용자라면 연결 복구를 선택하세요.";status.SetBounds(30,142,590,54);Controls.Add(status);
  install.Text="설치 시작";repair.Text="연결 복구";close.Text="닫기";install.SetBounds(30,207,160,42);repair.SetBounds(202,207,160,42);close.SetBounds(474,207,140,42);install.BackColor=Color.FromArgb(252,213,53);repair.BackColor=Color.White;Controls.AddRange(new Control[]{install,repair,close});
  progress.SetBounds(30,265,584,8);progress.Visible=false;Controls.Add(progress);
  var more=new Label{Text="진행 상세 · 문제가 발생하면 아래 내용을 확인하세요.",Location=new Point(30,288),AutoSize=true};Controls.Add(more);
  details.Multiline=true;details.ReadOnly=true;details.ScrollBars=ScrollBars.Vertical;details.SetBounds(30,315,584,112);details.BackColor=Color.FromArgb(245,247,249);details.Anchor=AnchorStyles.Left|AnchorStyles.Right|AnchorStyles.Top|AnchorStyles.Bottom;Controls.Add(details);
  install.Click+=async(s,e)=>await Run("install");repair.Click+=async(s,e)=>await Run("repair");close.Click+=(s,e)=>Close();
  FormClosing+=(s,e)=>{if(running){e.Cancel=true;MessageBox.Show(this,"진행 중에는 설치기를 닫을 수 없습니다. 확인 창에서 취소하거나 작업 완료를 기다려 주세요.",Text);}};
 }
 void Log(string line){if(line==null||IsDisposed)return;BeginInvoke((Action)(()=>details.AppendText(line+Environment.NewLine)));}
 void Extract(){
  Directory.CreateDirectory(target);
  using(var stream=Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))using(var zip=new ZipArchive(stream,ZipArchiveMode.Read))foreach(var entry in zip.Entries){
   if(entry.FullName.Contains("..")||entry.FullName.Contains(":")||Path.GetFileName(entry.FullName)!=entry.FullName)throw new Exception("설치 패키지 경로 오류");
   string file=Path.Combine(target,entry.FullName);byte[] data;using(var m=new MemoryStream()){using(var z=entry.Open())z.CopyTo(m);data=m.ToArray();}
   if(File.Exists(file)){using(var sha=SHA256.Create()){if(Convert.ToBase64String(sha.ComputeHash(File.ReadAllBytes(file)))!=Convert.ToBase64String(sha.ComputeHash(data)))throw new Exception("기존 프로그램 파일이 변경되어 보존했습니다: "+file+"\n새 설치 위치를 확인해야 합니다.");}}
   else File.WriteAllBytes(file,data);
  }
 }
 async Task Run(string mode){
  if(running)return;
  var question=mode=="repair"?"기존 설치와 연결 설정을 검사하고 복구합니다. 패키지·모델을 새로 다운로드하지 않습니다.":"기존 환경을 먼저 검사합니다. 필요한 항목의 다운로드·설치는 추가 확인 후 진행합니다.";
  if(MessageBox.Show(this,question+"\n\n프로그램 위치: "+target+"\n\n진행할까요?",Text,MessageBoxButtons.YesNo,MessageBoxIcon.Question)!=DialogResult.Yes)return;
  running=true;install.Enabled=repair.Enabled=close.Enabled=false;progress.Visible=true;progress.Style=ProgressBarStyle.Marquee;status.Text="환경 확인 및 연결 준비 중입니다. 추가 확인 창이 열리면 변경 내용을 확인하세요.";
  try{
   await Task.Run(()=>Extract());
   var psi=new ProcessStartInfo("powershell.exe","-NoProfile -STA -ExecutionPolicy Bypass -File \""+Path.Combine(target,"2026-10-22-setup-ui.ps1")+"\" -Mode "+mode){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true,StandardOutputEncoding=Encoding.UTF8,StandardErrorEncoding=Encoding.UTF8,WorkingDirectory=target};
   using(var p=new Process{StartInfo=psi}){p.OutputDataReceived+=(s,e)=>Log(e.Data);p.ErrorDataReceived+=(s,e)=>Log(e.Data);p.Start();p.BeginOutputReadLine();p.BeginErrorReadLine();await Task.Run(()=>p.WaitForExit());if(p.ExitCode!=0)throw new Exception("설치·복구를 완료하지 못했습니다. 상세 내용을 확인하세요. 취소한 경우 다시 시작할 수 있습니다.");}
   status.Text="로컬 준비 확인 완료. 웹으로 돌아가 ‘스튜디오 시작’을 눌러 연결하세요. 상주 엔진은 남겨두지 않았습니다.";
   MessageBox.Show(this,"로컬 설치·연결 검사를 마쳤습니다.\n웹에서 스튜디오 시작 → 앱 열기 → 사이트 승인 순서로 연결하세요.",Text,MessageBoxButtons.OK,MessageBoxIcon.Information);
  }catch(Exception ex){status.Text="완료되지 않았습니다. 아래 상세 내용을 확인해 주세요.";Log(ex.Message);MessageBox.Show(this,ex.Message,Text,MessageBoxButtons.OK,MessageBoxIcon.Warning);}
  finally{running=false;install.Enabled=repair.Enabled=close.Enabled=true;progress.Visible=false;}
 }
}
