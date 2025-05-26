"""
Autor: Juan Esteban Palacio
Descripción: Funciones para el manejo de ficheros WAVE estéreo y monofónicos,
incluyendo codificación y decodificación de señales estéreo en formato compatible
con sistemas monoaurales.
"""

import struct

def leer_cabecera(f):
    cabecera = f.read(44)
    if len(cabecera) != 44:
        raise ValueError("Cabecera WAV incompleta o corrupta.")
    riff, size, wave, fmt, fmt_size, audio_fmt, num_channels, sample_rate, byte_rate, block_align, bits_per_sample, data, data_size = struct.unpack('<4sI4s4sIHHIIHH4sI', cabecera)
    
    if riff != b'RIFF' or wave != b'WAVE' or fmt != b'fmt ' or data != b'data':
        raise ValueError("Formato WAV incorrecto.")
    if audio_fmt != 1 or bits_per_sample != 16:
        raise ValueError("Solo se admite PCM lineal de 16 bits.")
    
    return {
        'riff': riff, 'size': size, 'wave': wave, 'fmt': fmt,
        'fmt_size': fmt_size, 'audio_fmt': audio_fmt, 'num_channels': num_channels,
        'sample_rate': sample_rate, 'byte_rate': byte_rate,
        'block_align': block_align, 'bits_per_sample': bits_per_sample,
        'data': data, 'data_size': data_size
    }, cabecera

def escribir_cabecera(f, params, data_size):
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + data_size,
        b'WAVE',
        b'fmt ', 16,
        1,  # PCM
        params['num_channels'],
        params['sample_rate'],
        params['sample_rate'] * params['num_channels'] * 2,
        params['num_channels'] * 2,
        16,
        b'data',
        data_size
    )
    f.write(header)

def estereo2mono(ficEste, ficMono, canal=2):
    with open(ficEste, 'rb') as f:
        params, header = leer_cabecera(f)
        if params['num_channels'] != 2:
            raise ValueError("El fichero de entrada no es estéreo.")
        data = f.read()

    muestras = struct.iter_unpack('<hh', data)
    if canal == 0:
        mono = [l for l, _ in muestras]
    elif canal == 1:
        mono = [r for _, r in muestras]
    elif canal == 2:
        mono = [((l + r) // 2) for l, r in muestras]
    elif canal == 3:
        mono = [((l - r) // 2) for l, r in muestras]
    else:
        raise ValueError("Canal no válido: debe ser 0, 1, 2 o 3.")

    with open(ficMono, 'wb') as f:
        params['num_channels'] = 1
        escribir_cabecera(f, params, len(mono) * 2)
        f.write(struct.pack('<' + 'h' * len(mono), *mono))

def mono2estereo(ficIzq, ficDer, ficEste):
    with open(ficIzq, 'rb') as f:
        paramsL, _ = leer_cabecera(f)
        if paramsL['num_channels'] != 1:
            raise ValueError("ficIzq no es mono.")
        dataL = f.read()

    with open(ficDer, 'rb') as f:
        paramsR, _ = leer_cabecera(f)
        if paramsR['num_channels'] != 1:
            raise ValueError("ficDer no es mono.")
        dataR = f.read()

    muestrasL = struct.unpack('<' + 'h' * (len(dataL) // 2), dataL)
    muestrasR = struct.unpack('<' + 'h' * (len(dataR) // 2), dataR)

    if len(muestrasL) != len(muestrasR):
        raise ValueError("Los dos canales no tienen la misma longitud.")

    estereo = [par for tupla in zip(muestrasL, muestrasR) for par in tupla]

    with open(ficEste, 'wb') as f:
        paramsL['num_channels'] = 2
        escribir_cabecera(f, paramsL, len(estereo) * 2)
        f.write(struct.pack('<' + 'h' * len(estereo), *estereo))

import wave
import struct

def codEstereo(ficEste, ficCod):
    with wave.open(ficEste, 'rb') as f:
        if f.getnchannels() != 2 or f.getsampwidth() != 2:
            raise ValueError("El fichero no es estéreo con 16 bits por muestra")

        n_frames = f.getnframes()
        datos = f.readframes(n_frames)
        muestras = struct.unpack('<' + 'h' * 2 * n_frames, datos)

        izq = muestras[::2]
        der = muestras[1::2]

        codificado = []
        for l, r in zip(izq, der):
            semisuma = (l + r) // 2
            semidif  = (l - r) // 2

            # Convertimos a uint16 (0 a 65535)
            s16 = semisuma & 0xFFFF
            d16 = semidif  & 0xFFFF

            # Combinamos en uint32
            cod = (s16 << 16) | d16
            codificado.append(cod)

    with wave.open(ficCod, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(4)  # 32 bits
        f.setframerate(44100)
        datos = struct.pack('<' + 'I' * len(codificado), *codificado)
        f.writeframes(datos)

def leer_cabecera_codificada(f):
    import struct

    cabecera = f.read(44)  # Tamaño típico de cabecera WAV

    if len(cabecera) < 44:
        raise ValueError("Archivo WAV demasiado corto.")

    riff, size, wave = struct.unpack('<4sI4s', cabecera[0:12])
    fmt, fmt_size = struct.unpack('<4sI', cabecera[12:20])
    audio_fmt, num_channels, sample_rate = struct.unpack('<HHI', cabecera[20:28])
    byte_rate, block_align, bits_per_sample = struct.unpack('<IHH', cabecera[28:36])
    data, data_size = struct.unpack('<4sI', cabecera[36:44])

    if riff != b'RIFF' or wave != b'WAVE' or fmt != b'fmt ' or data != b'data':
        raise ValueError("Formato WAV incorrecto.")

    # Aquí comprobamos que sea PCM 32 bits mono (audio_fmt=1 para PCM)
    if audio_fmt != 1 or bits_per_sample != 32 or num_channels != 1:
        raise ValueError("Se espera archivo codificado PCM lineal de 32 bits mono.")

    return {
        'riff': riff,
        'size': size,
        'wave': wave,
        'fmt': fmt,
        'fmt_size': fmt_size,
        'audio_fmt': audio_fmt,
        'num_channels': num_channels,
        'sample_rate': sample_rate,
        'byte_rate': byte_rate,
        'block_align': block_align,
        'bits_per_sample': bits_per_sample,
        'data': data,
        'data_size': data_size
    }, cabecera



def decEstereo(ficCod, ficEste):
    with open(ficCod, 'rb') as f:
        params, _ = leer_cabecera_codificada(f)  
        
        data = f.read()

    enteros = struct.unpack('<' + 'i' * (len(data) // 4), data)
    muestras = []
    for val in enteros:
        semisuma = val >> 16
        semidif = struct.unpack('h', struct.pack('H', val & 0xFFFF))[0]
        L = semisuma + semidif
        R = semisuma - semidif
        muestras.extend([L, R])

    with open(ficEste, 'wb') as f:
        params['num_channels'] = 2
        params['bits_per_sample'] = 16  
        escribir_cabecera(f, params, len(muestras) * 2)
        f.write(struct.pack('<' + 'h' * len(muestras), *muestras))

