import json
import os
import sys
import tempfile

from PIL import Image
from PIL.PngImagePlugin import PngInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metadata_parser import MetadataParser


class SkipCase(Exception):
    pass


def make_image():
    return Image.new("RGB", (8, 8), (120, 80, 40))


def save_png(path, chunks=None):
    pnginfo = PngInfo()
    for key, value in (chunks or {}).items():
        pnginfo.add_text(key, value)
    with make_image() as image:
        image.save(path, format="PNG", pnginfo=pnginfo)


def basic_graph(positive="POSITIVE cat", negative="NEGATIVE ugly"):
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "positive": ["6", 0],
                "negative": ["7", 0],
            },
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": positive},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative},
        },
    }


def extract_prompt(path):
    parser = MetadataParser()
    metadata = parser.extract_metadata(path)
    return parser.get_prompt_text(metadata)


def assert_prompt(path, expected_text, expected_source):
    text, source = extract_prompt(path)
    assert text == expected_text, (
        "expected text {!r}, got {!r}".format(expected_text, text)
    )
    assert source == expected_source, (
        "expected source {!r}, got {!r}".format(expected_source, source)
    )
    return text


def case_01_a1111_png(temp_dir):
    path = os.path.join(temp_dir, "case01.png")
    parameters = (
        "a red fox, forest\n"
        "Negative prompt: blurry\n"
        "Steps: 20, Sampler: Euler, CFG scale: 7, Seed: 1"
    )
    save_png(path, {"parameters": parameters})
    assert_prompt(path, "a red fox, forest", "a1111")


def case_02_comfyui_basic(temp_dir):
    path = os.path.join(temp_dir, "case02.png")
    save_png(path, {"prompt": json.dumps(basic_graph())})
    text = assert_prompt(path, "POSITIVE cat", "comfyui")
    assert "NEGATIVE" not in text


def case_03_comfyui_linked_text(temp_dir):
    direct_path = os.path.join(temp_dir, "case03_direct.png")
    direct_graph = basic_graph()
    direct_graph["6"]["inputs"]["text"] = ["10", 0]
    direct_graph["10"] = {
        "class_type": "PrimitiveString",
        "inputs": {"value": "linked dog"},
    }
    save_png(direct_path, {"prompt": json.dumps(direct_graph)})
    direct_text = assert_prompt(direct_path, "linked dog", "comfyui")
    assert "NEGATIVE" not in direct_text

    concat_path = os.path.join(temp_dir, "case03_concat.png")
    concat_graph = basic_graph()
    concat_graph["6"]["inputs"]["text"] = ["11", 0]
    concat_graph["10"] = {
        "class_type": "PrimitiveString",
        "inputs": {"value": "linked dog"},
    }
    concat_graph["11"] = {
        "class_type": "StringConcatenate",
        "inputs": {
            "string_a": "part one",
            "string_b": ["10", 0],
        },
    }
    save_png(concat_path, {"prompt": json.dumps(concat_graph)})

    text, source = extract_prompt(concat_path)
    assert source == "comfyui", "expected source 'comfyui', got {!r}".format(source)
    assert "part one" in text, "missing first concat part in {!r}".format(text)
    assert "linked dog" in text, "missing linked concat part in {!r}".format(text)
    assert "NEGATIVE" not in text


def case_04_comfyui_sdxl(temp_dir):
    path = os.path.join(temp_dir, "case04.png")
    graph = {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "positive": ["6", 0],
                "negative": ["7", 0],
            },
        },
        "6": {
            "class_type": "CLIPTextEncodeSDXL",
            "inputs": {
                "text_g": "same text",
                "text_l": "same text",
            },
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "NEGATIVE ugly"},
        },
    }
    save_png(path, {"prompt": json.dumps(graph)})
    assert_prompt(path, "same text", "comfyui")


def case_05_comfyui_pass_through(temp_dir):
    path = os.path.join(temp_dir, "case05.png")
    graph = basic_graph()
    graph["3"]["inputs"]["positive"] = ["8", 0]
    graph["8"] = {
        "class_type": "ControlNetApplyAdvanced",
        "inputs": {
            "positive": ["6", 0],
            "negative": ["7", 0],
        },
    }
    save_png(path, {"prompt": json.dumps(graph)})
    text = assert_prompt(path, "POSITIVE cat", "comfyui")
    assert "NEGATIVE" not in text


def case_06_comfyui_guider(temp_dir):
    cfg_path = os.path.join(temp_dir, "case06_cfg.png")
    cfg_graph = {
        "3": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {"guider": ["20", 0]},
        },
        "20": {
            "class_type": "CFGGuider",
            "inputs": {
                "positive": ["6", 0],
                "negative": ["7", 0],
            },
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "POSITIVE cat"},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "NEGATIVE ugly"},
        },
    }
    save_png(cfg_path, {"prompt": json.dumps(cfg_graph)})
    cfg_text = assert_prompt(cfg_path, "POSITIVE cat", "comfyui")
    assert "NEGATIVE" not in cfg_text

    basic_path = os.path.join(temp_dir, "case06_basic.png")
    basic_guider_graph = {
        "3": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {"guider": ["20", 0]},
        },
        "20": {
            "class_type": "BasicGuider",
            "inputs": {"conditioning": ["21", 0]},
        },
        "21": {
            "class_type": "FluxGuidance",
            "inputs": {"conditioning": ["6", 0]},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "flux prompt"},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "NEGATIVE flux"},
        },
    }
    save_png(basic_path, {"prompt": json.dumps(basic_guider_graph)})
    basic_text = assert_prompt(basic_path, "flux prompt", "comfyui")
    assert "NEGATIVE" not in basic_text


def case_07_comfyui_no_sampler(temp_dir):
    path = os.path.join(temp_dir, "case07.png")
    graph = {
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "POSITIVE cat"},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "NEGATIVE ugly"},
        },
        "8": {
            "class_type": "SomeCustomThing",
            "inputs": {"negative": ["7", 0]},
        },
    }
    save_png(path, {"prompt": json.dumps(graph)})
    text = assert_prompt(path, "POSITIVE cat", "comfyui")
    assert "NEGATIVE" not in text


def case_08_comfyui_workflow_only(temp_dir):
    path = os.path.join(temp_dir, "case08.png")
    workflow = {
        "nodes": [
            {
                "id": 6,
                "type": "CLIPTextEncode",
                "widgets_values": ["wf positive"],
            },
            {
                "id": 7,
                "type": "CLIPTextEncode",
                "widgets_values": ["wf negative"],
            },
            {
                "id": 3,
                "type": "KSampler",
                "inputs": [
                    {"name": "positive", "link": 1},
                    {"name": "negative", "link": 2},
                ],
            },
        ],
        "links": [
            [1, 6, 0, 3, 1, "CONDITIONING"],
            [2, 7, 0, 3, 2, "CONDITIONING"],
        ],
    }
    save_png(path, {"workflow": json.dumps(workflow)})
    text = assert_prompt(path, "wf positive", "comfyui")
    assert "wf negative" not in text


def case_09_malformed_prompt_with_tags(temp_dir):
    path = os.path.join(temp_dir, "case09.png")
    save_png(path, {"prompt": "{not json"})
    with open(path + ".txt", "w", encoding="utf-8") as tag_file:
        tag_file.write("tag_a, tag_b")
    assert_prompt(path, "tag_a, tag_b", "tags")


def case_10_midjourney_png(temp_dir):
    path = os.path.join(temp_dir, "case10.png")
    description = (
        "a castle on a hill --ar 16:9 --v 6 "
        "Job ID: 0a1b2c3d-1111-2222-3333-444455556666"
    )
    save_png(path, {"Description": description})
    assert_prompt(path, "a castle on a hill --ar 16:9 --v 6", "midjourney")


def case_11_midjourney_xmp_png(temp_dir):
    path = os.path.join(temp_dir, "case11.png")
    xmp = (
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">'
        "<rdf:Description>"
        "<dc:description><rdf:Alt>"
        '<rdf:li xml:lang="x-default">'
        "xmp castle &amp; moat --v 6 Job ID: abc-123"
        "</rdf:li>"
        "</rdf:Alt></dc:description>"
        "</rdf:Description>"
        "</rdf:RDF>"
        "</x:xmpmeta>"
    )
    save_png(path, {"XML:com.adobe.xmp": xmp})
    assert_prompt(path, "xmp castle & moat --v 6", "midjourney")


def case_12_jpeg_image_description(temp_dir):
    path = os.path.join(temp_dir, "case12.jpg")
    exif = Image.Exif()
    exif[0x010E] = "jpeg desc --ar 1:1"
    with make_image() as image:
        image.save(path, format="JPEG", exif=exif)
    assert_prompt(path, "jpeg desc --ar 1:1", "midjourney")


def case_13_jpeg_xmp(temp_dir):
    path = os.path.join(temp_dir, "case13.jpg")
    xmp = (
        b'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
        b'xmlns:dc="http://purl.org/dc/elements/1.1/">'
        b"<rdf:Description>"
        b"<dc:description><rdf:Alt>"
        b'<rdf:li xml:lang="x-default">'
        b"jpeg xmp castle --v 6 Job ID: abc-123"
        b"</rdf:li>"
        b"</rdf:Alt></dc:description>"
        b"</rdf:Description>"
        b"</rdf:RDF>"
        b"</x:xmpmeta>"
    )

    try:
        with make_image() as image:
            image.save(path, format="JPEG", xmp=xmp)
    except TypeError as exc:
        raise SkipCase("Pillow JPEG XMP save is unsupported: {}".format(exc))

    with Image.open(path) as image:
        if not image.info.get("xmp"):
            raise SkipCase("Pillow did not persist JPEG XMP")

    assert_prompt(path, "jpeg xmp castle --v 6", "midjourney")


def case_14_jpeg_a1111_user_comment(temp_dir):
    path = os.path.join(temp_dir, "case14.jpg")
    comment = (
        b"UNICODE\x00"
        + "jpeg fox\nSteps: 20, Sampler: Euler".encode("utf-16-be")
    )

    pillow_persisted = False
    try:
        exif = Image.Exif()
        exif.get_ifd(0x8769)[0x9286] = comment
        with make_image() as image:
            image.save(path, format="JPEG", exif=exif)
        pillow_persisted = (
            extract_prompt(path) == ("jpeg fox", "a1111")
        )
    except Exception:
        pillow_persisted = False

    if not pillow_persisted:
        try:
            import piexif
        except ImportError:
            raise SkipCase(
                "Pillow did not persist UserComment and piexif is unavailable"
            )

        fallback_path = os.path.join(temp_dir, "case14_piexif.jpg")
        exif_bytes = piexif.dump(
            {
                "0th": {},
                "Exif": {piexif.ExifIFD.UserComment: comment},
                "GPS": {},
                "1st": {},
                "thumbnail": None,
            }
        )
        with make_image() as image:
            image.save(fallback_path, format="JPEG", exif=exif_bytes)
        path = fallback_path

    assert_prompt(path, "jpeg fox", "a1111")


def case_15_webp_comfyui(temp_dir):
    path = os.path.join(temp_dir, "case15.webp")
    exif = Image.Exif()
    exif[0x0110] = "prompt:" + json.dumps(basic_graph())
    with make_image() as image:
        image.save(path, format="WEBP", exif=exif)
    text = assert_prompt(path, "POSITIVE cat", "comfyui")
    assert "NEGATIVE" not in text


def case_16_empty(temp_dir):
    path = os.path.join(temp_dir, "case16.png")
    save_png(path)
    assert_prompt(path, "", "")


def case_17_empty_metadata(temp_dir):
    del temp_dir
    parser = MetadataParser()
    assert parser.get_prompt_text({}) == ("", "")
    assert parser.get_prompt_text(None) == ("", "")


def case_18_comfyui_wildcard_echo(temp_dir):
    """A ShowText echo node holds the wildcard-resolved text; prefer it."""
    path = os.path.join(temp_dir, "case18.png")
    graph = basic_graph()
    # CLIPTextEncode pulls its text from a wildcard expander whose widget still
    # holds the unresolved template.
    graph["6"]["inputs"]["text"] = ["20", 0]
    graph["20"] = {
        "class_type": "DPRandomGenerator",
        "inputs": {"text": "a photo of ||animal|| in ||place||"},
    }
    # ShowText|pysssss echoes the runtime value of that exact link.
    graph["62"] = {
        "class_type": "ShowText|pysssss",
        "inputs": {"text": ["20", 0], "text_0": "a photo of a fox in a forest"},
    }
    # A second echo on a different slot of the same node must not be picked up.
    graph["63"] = {
        "class_type": "ShowText|pysssss",
        "inputs": {"text": ["20", 1], "text_0": "dupe report: nothing removed"},
    }
    save_png(path, {"prompt": json.dumps(graph)})

    text = assert_prompt(path, "a photo of a fox in a forest", "comfyui")
    assert "||" not in text, "wildcard template leaked into {!r}".format(text)
    assert "dupe report" not in text


CASES = [
    ("01 A1111 PNG", case_01_a1111_png),
    ("02 ComfyUI PNG basic", case_02_comfyui_basic),
    ("03 ComfyUI linked text", case_03_comfyui_linked_text),
    ("04 ComfyUI SDXL", case_04_comfyui_sdxl),
    ("05 ComfyUI pass-through", case_05_comfyui_pass_through),
    ("06 ComfyUI guider", case_06_comfyui_guider),
    ("07 ComfyUI no sampler", case_07_comfyui_no_sampler),
    ("08 ComfyUI workflow-only", case_08_comfyui_workflow_only),
    ("09 Malformed prompt with tags", case_09_malformed_prompt_with_tags),
    ("10 Midjourney PNG", case_10_midjourney_png),
    ("11 Midjourney XMP in PNG", case_11_midjourney_xmp_png),
    ("12 JPEG ImageDescription", case_12_jpeg_image_description),
    ("13 JPEG XMP", case_13_jpeg_xmp),
    ("14 JPEG A1111 UserComment", case_14_jpeg_a1111_user_comment),
    ("15 WebP ComfyUI", case_15_webp_comfyui),
    ("16 Empty image", case_16_empty),
    ("17 Empty metadata", case_17_empty_metadata),
    ("18 ComfyUI wildcard echo", case_18_comfyui_wildcard_echo),
]


def run_all_cases():
    failures = []

    with tempfile.TemporaryDirectory() as temp_dir:
        for name, case_function in CASES:
            try:
                case_function(temp_dir)
            except SkipCase as exc:
                print("SKIP: {} - {}".format(name, exc))
            except Exception as exc:
                message = "{}: {}".format(type(exc).__name__, exc)
                failures.append("{} - {}".format(name, message))
                print("FAIL: {} - {}".format(name, message))
            else:
                print("PASS: {}".format(name))

    return failures


def test_prompt_sources():
    failures = run_all_cases()
    assert not failures, "\n".join(failures)


if __name__ == "__main__":
    sys.exit(1 if run_all_cases() else 0)
