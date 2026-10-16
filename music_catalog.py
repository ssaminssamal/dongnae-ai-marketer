"""Original, synthesized instrumental loops; no third-party recordings or samples."""
from pathlib import Path
import wave
import numpy as np

TRACKS = {'warm': '따뜻한 로파이', 'bright': '산뜻한 팝', 'calm': '차분한 앰비언트'}
RATE = 22050


def _tone(freq, seconds, softness=1):
    t = np.arange(int(RATE*seconds))/RATE
    envelope = np.minimum(1,t/.025)*np.exp(-t*softness)
    envelope *= np.minimum(1,(seconds-t)/.08)
    return (np.sin(2*np.pi*freq*t)+.18*np.sin(4*np.pi*freq*t))*envelope


def ensure_tracks():
    folder=Path(__file__).parent/'assets'/'music'
    folder.mkdir(parents=True,exist_ok=True)
    for name in TRACKS:
        path=folder/f'{name}.wav'
        if path.exists():
            continue
        bpm={'warm':88,'bright':112,'calm':72}[name]
        beat=60/bpm
        length=beat*32
        sound=np.zeros(int(length*RATE))
        rng=np.random.default_rng(21)
        chords=[(48,52,55),(45,48,52),(53,57,60),(43,47,50)]
        def add(offset,signal,gain):
            at=int(offset*RATE); size=min(len(signal),len(sound)-at)
            if size>0: sound[at:at+size]+=signal[:size]*gain
        for bar in range(8):
            chord=chords[bar%4]
            for note in chord:
                freq=440*2**((note-69)/12)
                add(bar*beat*4,_tone(freq,beat*4, .45 if name=='calm' else .9),.085)
            for step in range(8):
                note=chord[(step+bar)%3]+12
                add((bar*4+step/2)*beat,_tone(440*2**((note-69)/12),beat*.8,4),.055)
            if name!='calm':
                for tick in range(4):
                    t=np.arange(int(.22*RATE))/RATE
                    kick=np.sin(2*np.pi*(48*t+5*(1-np.exp(-30*t))))*np.exp(-22*t)
                    add((bar*4+tick)*beat,kick,.12)
                for tick in range(8):
                    t=np.arange(int(.06*RATE))/RATE
                    noise=rng.normal(0,1,len(t)); noise=np.diff(noise,prepend=0)
                    add((bar*4+tick/2)*beat,noise*np.exp(-75*t),.012)
        sound *= np.minimum(1,np.arange(len(sound))/(RATE*.06))
        sound *= np.minimum(1,np.arange(len(sound))[::-1]/(RATE*.08))
        peak=np.max(np.abs(sound))
        sound=sound/max(peak,1e-6)*.65
        stereo=np.column_stack((sound,np.roll(sound,37)*.98))
        with wave.open(str(path),'wb') as wav:
            wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(RATE)
            wav.writeframes((stereo*32767).astype('<i2').tobytes())
    return {key:folder/f'{key}.wav' for key in TRACKS}
