#!/usr/bin/env python3
"""Animate a closed outline as Fourier epicycles; stdlib only."""
import argparse
import json
import math
import re
from pathlib import Path
from xml.etree import ElementTree as ET


NUMBER = r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?'
PATH_TOKEN = re.compile(rf'[A-Za-z]|{NUMBER}')


def svg_path_points(d):
    tokens = PATH_TOKEN.findall(d)
    if re.sub(r'[\s,]+', '', PATH_TOKEN.sub('', d)):
        raise ValueError('Invalid SVG path syntax')
    points, i, command = [], 0, None
    cursor = 0j
    start = None
    previous_control = None
    previous_curve = None
    arity = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'C': 6, 'S': 4, 'Q': 4, 'T': 2}
    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]
            i += 1
            if command.upper() == 'Z':
                if start is None or i < len(tokens):
                    raise ValueError('Closed SVG path required; multiple subpaths not supported')
                break
            if command.upper() not in arity:
                raise ValueError(f'Unsupported SVG path command: {command}')
            if command.upper() == 'M' and start is not None:
                raise ValueError('SVG multiple subpaths not supported')
        if command is None or len(tokens) - i < arity[command.upper()] or any(x.isalpha() for x in tokens[i:i + arity[command.upper()]]):
            raise ValueError('Incomplete SVG path command')
        size = arity[command.upper()]
        values = [float(x) for x in tokens[i:i + size]]
        if not all(math.isfinite(x) for x in values):
            raise ValueError('SVG coordinates must be finite')
        i += size
        relative = command.islower()
        point = lambda x, y: complex(x, y) + (cursor if relative else 0)
        op = command.upper()
        if op in ('M', 'L', 'T'):
            end = point(*values)
            if op == 'M':
                start = end
                points.append(end)
                command = 'l' if relative else 'L'
            elif op == 'T':
                control = 2 * cursor - previous_control if previous_curve == 'Q' else cursor
                points.extend(curve_points(cursor, [control], end))
                previous_control = control
            else:
                points.append(end)
        elif op == 'H':
            end = complex(cursor.real + values[0] if relative else values[0], cursor.imag)
            points.append(end)
        elif op == 'V':
            end = complex(cursor.real, cursor.imag + values[0] if relative else values[0])
            points.append(end)
        else:
            controls = [point(values[j], values[j + 1]) for j in range(0, size - 2, 2)]
            end = point(values[-2], values[-1])
            if op in ('S',):
                controls.insert(0, 2 * cursor - previous_control if previous_curve == 'C' else cursor)
            points.extend(curve_points(cursor, controls, end))
            previous_control = controls[-1]
        cursor = end
        if op not in ('C', 'S', 'Q', 'T'):
            previous_control = None
        previous_curve = 'C' if op in ('C', 'S') else 'Q' if op in ('Q', 'T') else None
    if command is None or command.upper() != 'Z':
        raise ValueError('SVG path must end with Z (closed outline)')
    return points


def curve_points(start, controls, end):
    # ponytail: fixed 16 subdivisions per curve; use adaptive flattening if tight high-curvature paths lose detail.
    if len(controls) == 1:
        (a,) = controls
        return [(1 - t) ** 2 * start + 2 * (1 - t) * t * a + t * t * end for t in (j / 16 for j in range(1, 17))]
    a, b = controls
    return [(1 - t) ** 3 * start + 3 * (1 - t) ** 2 * t * a + 3 * (1 - t) * t * t * b + t ** 3 * end for t in (j / 16 for j in range(1, 17))]


def load_points(path):
    if path.suffix.lower() == '.svg':
        root = ET.parse(path).getroot()
        shapes = [e for e in root.iter() if e.tag.rsplit('}', 1)[-1] in ('polygon', 'polyline', 'path')]
        if len(shapes) != 1:
            raise ValueError('SVG must contain exactly one polygon, polyline, or path')
        shape = shapes[0]
        if any(e.get('transform') for e in root.iter()):
            raise ValueError('SVG transform is not supported')
        if shape.tag.rsplit('}', 1)[-1] == 'path':
            points = svg_path_points(shape.get('d', ''))
        else:
            nums = [float(x) for x in re.findall(NUMBER, shape.get('points', ''))]
            if len(nums) < 6 or len(nums) % 2:
                raise ValueError('Need at least three x,y points')
            points = [complex(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
    else:
        points = []
        for line in path.read_text().splitlines():
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            a, b = line.split(',')
            points.append(complex(float(a), float(b)))
    if not all(math.isfinite(p.real) and math.isfinite(p.imag) for p in points):
        raise ValueError('All coordinates must be finite')
    if len(points) > 1 and points[-1] == points[0]:
        points.pop()
    if len(set(points)) < 3:
        raise ValueError('Need at least three distinct points')
    return points


def sample(points, count):
    edges = [abs(points[(i + 1) % len(points)] - p) for i, p in enumerate(points)]
    perimeter = sum(edges)
    if perimeter == 0:
        raise ValueError('Zero perimeter')
    cumulative = [0.0]
    for length in edges:
        cumulative.append(cumulative[-1] + length)
    out, edge = [], 0
    for j in range(count):
        distance = perimeter * j / count
        while edge < len(edges) - 1 and cumulative[edge + 1] <= distance:
            edge += 1
        fraction = (distance - cumulative[edge]) / edges[edge] if edges[edge] else 0
        out.append(points[edge] + (points[(edge + 1) % len(points)] - points[edge]) * fraction)
    return out


def coefficients(points, limit):
    n = len(points)
    center = sum(points) / n
    # Simultaneously compute positive/negative frequencies; enough for any real x/y outline.
    result = []
    for k in range(-limit, limit + 1):
        c = sum((p - center) * complex(math.cos(-2 * math.pi * k * j / n),
                                           math.sin(-2 * math.pi * k * j / n))
                for j, p in enumerate(points)) / n
        result.append((k, c))
    return center, result


def choose(points, coeffs, threshold):
    center = sum(points) / len(points)
    total = math.fsum(abs(p - center) ** 2 for p in points) / len(points)
    ordered = sorted(coeffs, key=lambda item: abs(item[1]), reverse=True)
    selected, energy = [], 0
    def relative_error():
        residual = max(0, total - energy)
        # Roundoff at full reconstruction must not appear as a fake 1e-8 error.
        if residual <= 1e-14 * total:
            return 0.0
        return math.sqrt(residual / total)
    for term in ordered:
        selected.append(term)
        energy = math.fsum(abs(c) ** 2 for _, c in selected)
        if total == 0 or relative_error() <= threshold:
            break
    return selected, relative_error() if total else 0.0



def render(points, center, selected, error):
    coords = [[round(p.real, 5), round(p.imag, 5)] for p in points]
    terms = [[k, round(c.real, 9), round(c.imag, 9)] for k, c in selected]
    payload = json.dumps({'points': coords, 'center': [center.real, center.imag],
                          'terms': terms, 'error': error}).replace('<', '\\u003c')
    return TEMPLATE.replace('/*DATA*/', payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='CSV x,y per line, or SVG with one polygon/polyline')
    parser.add_argument('-o', '--output', type=Path, default=Path('fourier.html'))
    parser.add_argument('--samples', type=int, default=256)
    parser.add_argument('--harmonics', type=int, default=60, help='maximum positive/negative frequency')
    parser.add_argument('--error', type=float, default=0.01, help='target relative RMS error, e.g. 0.01')
    args = parser.parse_args()
    if not 16 <= args.samples <= 2048 or not 1 <= args.harmonics < args.samples // 2 or not 0 < args.error < 1:
        parser.error('Require 16<=samples<=2048, 1<=harmonics<samples/2, 0<error<1')
    points = sample(load_points(args.input), args.samples)
    center, terms = coefficients(points, args.harmonics)
    selected, error = choose(points, terms, args.error)
    args.output.write_text(render(points, center, selected, error))
    print(f'{args.output}: {len(selected)} epicycles, relative RMS error {error:.3%}')


TEMPLATE = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fourier Outline Studio</title>
<style>body{margin:0;background:#101722;color:#eee;font:16px system-ui}header{padding:12px;display:flex;gap:16px;flex-wrap:wrap;align-items:center}canvas{display:block;width:100vw;height:calc(100dvh - 100px)}label{display:flex;gap:8px;align-items:center}input[type=range]{width:140px}button{background:#24364b;color:white;border:1px solid #64748b;border-radius:6px;padding:8px;cursor:pointer}</style>
<header><strong>Fourier Outline Studio</strong><label>Epicycles <input id="count" type="range" min="1"><output id="countValue"></output></label><label>Speed <input id="speed" type="range" min="1" max="100" value="25"></label><button id="toggle">Pause</button><button id="download">Export SVG</button><span id="metrics"></span></header><canvas id="canvas"></canvas><script>
const data=/*DATA*/;const canvas=document.getElementById('canvas'),ctx=canvas.getContext('2d');
const slider=document.getElementById('count');slider.max=data.terms.length;slider.value=data.terms.length;
let phase=0, running=true, trail=[], last=performance.now(), scale=1, offsetX=0, offsetY=0;
function resize(){const dpr=devicePixelRatio||1;canvas.width=canvas.clientWidth*dpr;canvas.height=canvas.clientHeight*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);const xs=data.points.map(p=>p[0]),ys=data.points.map(p=>p[1]);const minx=Math.min(...xs),maxx=Math.max(...xs),miny=Math.min(...ys),maxy=Math.max(...ys);scale=Math.min(canvas.clientWidth/(maxx-minx||1),canvas.clientHeight/(maxy-miny||1))*.65;offsetX=canvas.clientWidth/2-(minx+maxx)*scale/2;offsetY=canvas.clientHeight/2-(miny+maxy)*scale/2;trail=[]}window.addEventListener('resize',resize);resize();
function pos(x,y){return [x*scale+offsetX,y*scale+offsetY]}
function line(points,color,width,closed=false){ctx.beginPath();points.forEach((p,i)=>{const [x,y]=pos(...p);i?ctx.lineTo(x,y):ctx.moveTo(x,y)});if(closed)ctx.closePath();ctx.strokeStyle=color;ctx.lineWidth=width;ctx.stroke()}
function draw(now){const dt=Math.min((now-last)/1000,.1);last=now;if(running){phase=(phase+dt*Number(document.getElementById('speed').value)/25*.25)%(Math.PI*2)}ctx.clearRect(0,0,canvas.clientWidth,canvas.clientHeight);line(data.points,'#334155',1,true);
let x=data.center[0],y=data.center[1],segments=[];for(const [k,a,b] of data.terms.slice(0,Number(slider.value))){const nx=x+a*Math.cos(k*phase)-b*Math.sin(k*phase),ny=y+a*Math.sin(k*phase)+b*Math.cos(k*phase);segments.push([[x,y],[nx,ny],Math.hypot(a,b)]);x=nx;y=ny}
for(const [start,end,r] of segments){let [cx,cy]=pos(...start);ctx.beginPath();ctx.arc(cx,cy,r*scale,0,Math.PI*2);ctx.strokeStyle='#334155';ctx.lineWidth=1;ctx.stroke();line([start,end],'#7999ac',1)}
if(running){trail.push([x,y]);if(trail.length>1000)trail.shift()}if(trail.length>1)line(trail,'#fbbf24',2);ctx.fillStyle='#fbbf24';ctx.beginPath();ctx.arc(...pos(x,y),4,0,Math.PI*2);ctx.fill();document.getElementById('countValue').textContent=slider.value;document.getElementById('metrics').textContent=`${data.terms.length} terms selected · full RMS error ${(data.error*100).toFixed(2)}%`;requestAnimationFrame(draw)}requestAnimationFrame(draw);
document.getElementById('toggle').onclick=()=>{running=!running;document.getElementById('toggle').textContent=running?'Pause':'Play'};
document.getElementById('download').onclick=()=>{let out=[];for(let j=0;j<=512;j++){const t=2*Math.PI*j/512;let x=data.center[0],y=data.center[1];for(const [k,a,b] of data.terms.slice(0,Number(slider.value))){x+=a*Math.cos(k*t)-b*Math.sin(k*t);y+=a*Math.sin(k*t)+b*Math.cos(k*t)}out.push([x,y])}const xs=out.map(p=>p[0]),ys=out.map(p=>p[1]),minx=Math.min(...xs),miny=Math.min(...ys),w=Math.max(...xs)-minx||1,h=Math.max(...ys)-miny||1;const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="${minx} ${miny} ${w} ${h}"><polyline points="${out.map(p=>p.join(',')).join(' ')}" fill="none" stroke="black" stroke-width="${Math.max(w,h)/300}"/></svg>`;const url=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml'}));const a=document.createElement('a');a.href=url;a.download='fourier-outline.svg';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
</script></html>'''


if __name__ == '__main__':
    main()
