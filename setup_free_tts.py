"""Run once after installing requirements. Downloads the pinned local model."""
from pathlib import Path
import os

ROOT=Path(__file__).resolve().parent
os.environ.setdefault('HF_HOME',str(ROOT/'models'/'hf-cache'))
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING','1')
from supertonic import TTS

if __name__=='__main__':
    tts=TTS(model='supertonic-3',model_dir=ROOT/'models'/'supertonic3',auto_download=True,
            intra_op_num_threads=4,inter_op_num_threads=1)
    print('Local speech model ready:',', '.join(tts.voice_style_names))
