import json
import glob
import string
import time
import subprocess
from pathlib import Path
from pprint import pprint
import traceback

from pytopojson import topology


def run_external(cmd):
    print(f'running cmd - {cmd}')
    start = time.time()
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    end = time.time()
    print(f'STDOUT: {res.stdout}')
    print(f'STDERR: {res.stderr}')
    print(f'command took {end - start} secs to run')
    if res.returncode != 0:
        raise Exception(f'command {cmd} failed with exit code: {res.returncode}')

def chunk(l):
    n = 2000 - 1
    out = [l[i * n:(i + 1) * n] for i in range((len(l) + n - 1) // n )]
    if len(out) > 1 and len(out[-1]) == 1:
        node = out[-1][0]
        prev_node = out[-2][-1]
        out[-1] = [ prev_node. node ]
        out[-2] = out[-2][:-1]
    return out


def convert_polygon(poly, arc_to_way, arcs_to_ignore):
    out_str = ''
    for r_index, ring in enumerate(poly):
        for arc in ring:
            role = 'outer' if r_index == 0 else 'inner'
            if arc < 0:
                arc = ~arc
            if arc in arcs_to_ignore:
                continue
            if arc not in arc_to_way:
                raise Exception(f'arc: {arc} missing in arc to way mapping')
            for ref in arc_to_way[arc]:
                out_str += f'    <member type="way" ref="{ref}" role="{role}"/>\n'
    return out_str



# translated to python from https://github.com/andrewharvey/topo2osm/blob/master/index.js
def convert_to_osm(topo, tag_transformer):
    if topo['type'] != 'Topology':
        raise Exception('not a valid topojson')

    out_str = ''
    out_str += '<?xml version="1.0" encoding="UTF-8"?>\n'
    out_str += '<osm version="0.6" generator="topo2osm">\n'
    node_counter = 0
    way_counter = 0
    nodes = {}
    arc_to_way = {}
    arcs_to_ignore = set()
    for i,arc in enumerate(topo['arcs']):
        way_nodes = []
        prev_node_id = None
        for coord in arc:
            node_counter -= 1
            c_str = ','.join([ str(c) for c in coord ])
            if c_str not in nodes:
                nodes[c_str] = node_counter
                out_str += f'  <node id="{node_counter}" visible="true" lat="{coord[1]}" lon="{coord[0]}" />\n'
            node_id = nodes[c_str]
            if prev_node_id is None or prev_node_id != node_id:
                way_nodes.append(node_id)
            else:
                print(f'collapsing node_id: {node_id}')
            prev_node_id = node_id
        if len(way_nodes) == 1:
            arcs_to_ignore.add(i)
            #TODO: maybe this should be treated as a point and included somehow?
            print(f'WARNING: ignoring arc {i} with one node')
            continue
        chunks = chunk(way_nodes)
        for c_index, w_chunk in enumerate(chunks):
            way_counter -= 1
            if i not in arc_to_way:
                arc_to_way[i] = []

            arc_to_way[i].append(way_counter)
            out_str += f'  <way id="{way_counter}" visible="true">\n'
            for way_node in w_chunk:
                out_str += f'    <nd ref="{way_node}"/>\n'
           
            # join this chunk to the first node of the next chunk if there is a next chunk
            if len(chunks) > 1 and c_index < len(chunks) - 1:
                out_str += f'    <nd ref="{chunks[c_index + 1][0]}"/>\n'
            out_str += '  </way>\n'

    relation_counter = 0
    for key,value in topo['objects'].items():
        geoms = value.get('geometries', [])
        for geom in geoms:
            relation_counter -= 1
            out_str += f'  <relation id="{relation_counter}" visible="true">\n'

            g_type = geom['type']
            if g_type == 'Polygon':
                out_str += convert_polygon(geom['arcs'], arc_to_way, arcs_to_ignore)
            elif g_type == 'MultiPolygon':
                for poly in geom['arcs']:
                    out_str += convert_polygon(poly, arc_to_way, arcs_to_ignore)
            else:
                raise Exception(f'Unsupported geometry type: {g_type} found')
            tags = tag_transformer(geom['properties'])
            for k,v in tags.items():
                out_str += f'    <tag k="{k}" v="{v}"/>\n'
            out_str += '  </relation>\n'
    out_str += '</osm>\n'
    return out_str


def fix_soi_string(v):
    if v == None:
        v = 'UNKNOWN'
    v = v.replace(">", "A")
    v = v.replace("<", "a")
    v = v.replace("|", "I")
    v = v.replace("\\", "i")
    v = v.replace("@", "U")
    v = v.replace("#", "u")
    return v

def sanitize_tag(v):
    v = v.replace('&', 'and')
    v = " ".join(v.split())
    return v
 

def convert_tags(props):
    out = {}
    for k,v in props.items():
        if k != 'VILLAGE':
            continue
        v = fix_soi_string(v)
        v = sanitize_tag(v)
        out['name'] = string.capwords(v)
    out['admin_level'] = '9'
    out['boundary'] = 'administrative'
    out['type'] = 'boundary'
    return out

def split_by_taluka(data):
    out = {}
    for f in data['features']:
        taluka = f['properties'].get('TEHSIL', 'UNKNOWN')
        if taluka not in out:
            out[taluka] = {
                "type": "FeatureCollection",
                "features": []
            }
        out[taluka]['features'].append(f)
    return out



if __name__ == '__main__':

    for p in Path('data/raw/villages/').glob('*/*/data.zip'):
        state_dir = str(p.parent.parent)
        dist_dir = str(p.parent)
        dist_name = p.parent.name
        state_name = p.parent.parent.name
        geojson_fname = f'{dist_dir}/data.geojson'
        if not Path(geojson_fname).exists():
            run_external(f'ogr2ogr -f GeoJSON -t_srs EPSG:4326 "{geojson_fname}" "/vsizip/{dist_dir}/data.zip"')
        data = json.loads(Path(geojson_fname).read_text())

        print(f'handling district: {state_name=} {dist_name=}')
        topology_ = topology.Topology()
        topo = topology_({ 'villages': data })
        try:
            osm_str = convert_to_osm(topo, convert_tags)
            Path(f'{state_dir}/{dist_name}.osm').write_text(osm_str)
        except Exception as ex:
            print(f'!!! ERROR: got exception: {ex}')
            traceback.print_exc()

        Path(geojson_fname).unlink()



