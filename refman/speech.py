import os.path, torch, re
import shutil

import soundfile as sf
from kokoro import KPipeline, KModel
from tempfile import mktemp
from refman.config import UserConfig
from refman.functions import runCMD, text2md5

def text4speech(text: str):
    patt = re.compile(r' *\([0-9,;\- ]+\) *')
    text = patt.sub('', text)
    patt = re.compile(r' *\[[0-9,;\- ]+] *')
    text = patt.sub('', text)
    return text
def text2wav(text: str, voice='af_heart'):
    text = text4speech(text).strip()
    vfname = mktemp()
    dir_kk = UserConfig().get("dir_kokoro", "")
    if not os.path.isdir(dir_kk):
        return None
    lang_code = voice[0]
    voice_tensor = torch.load(f'{dir_kk}/voices/{voice}.pt', weights_only=True)
    repo_id = 'hexgrad/Kokoro-82M'
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model_path = f'{dir_kk}/kokoro-v1_0.pth'
    config_path = f'{dir_kk}/config.json'
    model = KModel(model=model_path, config=config_path, repo_id=repo_id).to(device).eval()
    pipeline = KPipeline(lang_code=lang_code, repo_id=repo_id, model=model)
    generator = pipeline(
        text,
        voice=voice_tensor,
        split_pattern=r'\n+'
    )
    ##
    wfiles = []
    for i, (gs, ps, audio) in enumerate(generator):
        fname = f'{vfname}_{i}.wav'
        sf.write(fname, audio, 24000)
        wfiles.append(fname)
    return wfiles
def text2audio(text: str, voice='af_heart', outdir: str=None, audio_type: str="mp3"):
    audio_name = text2md5(text) + f".{audio_type}"
    if outdir:
        audio_path = os.path.join(outdir, audio_name)
        if os.path.exists(audio_path):
            return audio_path
    ##
    waves = text2wav(text, voice)
    if len(waves) < 1:
        return audio_name
    vpath = os.path.dirname(waves[0])
    waves = [os.path.basename(x) for x in waves]
    vfname = re.sub(r'_\d+\.wav$', '', waves[0])
    wfiles = ' '.join(waves)
    if audio_type == "mp3":
        os.system(f'cd {vpath} && sox {wfiles} -t wav - | lame -b 128 - {audio_name} && rm {vfname}_*.wav')
    else:
        os.system(f'cd {vpath} && sox {wfiles} -t wav {audio_name} && rm {vfname}_*.wav')
    if outdir and os.path.isdir(outdir):
        audio_temp = os.path.join(vpath, audio_name)
        audio_path = os.path.join(outdir, audio_name)
        if os.path.exists(audio_temp):
            os.system(f'mv {audio_temp} {audio_path}')
    else:
        audio_path = os.path.join(vpath, audio_name)
    return audio_path
def abstract2mp3(text: str, bkey: str):
    cdict = UserConfig()
    voice = cdict.get('kokoro_voice', 'af_heart')
    target_dir = os.path.join(cdict.get("dir_user"), 'speech', voice, bkey)
    if not os.path.isdir(target_dir):
        os.system(f'mkdir -p {target_dir}')
    mp3path = text2audio(text, voice, outdir=target_dir)
    return mp3path

def words2wav(text: str):
    cdict = UserConfig()
    voice = cdict.get('kokoro_voice', 'af_heart')
    USR_DIR = cdict.get('dir_user')
    isWord = re.search(r'^[^a-z]*[a-z]{2,}[^a-z]*$', text, re.I)
    if isWord:
        outdir = os.path.join(USR_DIR, 'speech', 'words')
        text = re.sub(r'^[^a-z]+', '', text.lower(), re.I)
        text = re.sub(r'[^a-z]+$', '', text, re.I)
        wfile = os.path.join(outdir, f'{text}.wav')
        if os.path.exists(wfile):
            return wfile
    else:
        wfile = None
        outdir = os.path.join(USR_DIR, 'speech', 'fragments')
        ## 清理过期(大于7天)媒体文件
        if os.path.isdir(outdir):
            os.system(f'cd {outdir} && find -type f -mtime +7 -delete')

    if not os.path.isdir(outdir):
        os.system(f'mkdir -p "{outdir}"')
    wavpath = text2audio(text, voice, outdir=outdir, audio_type="wav")
    if isWord and os.path.exists(wavpath):
        shutil.move(wavpath, wfile)
        wavpath = wfile
    return wavpath
    #
def getAudioFolders(bkey: str):
    USR_DIR = UserConfig().get('dir_user')
    fdir = os.path.join(USR_DIR, 'speech')
    xdirs = runCMD(f'find "{fdir}" -type d -name "{bkey}"')
    return xdirs
def read_text(text):
    wav = words2wav(text)
    if os.path.exists(wav):
        os.system(f'play {wav}')
