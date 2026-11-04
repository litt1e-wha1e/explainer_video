"""把字幕文本转换成适合 TTS 朗读的文本：英文术语读法、数字读法、多音字消歧。"""
import re

# ---- 英文术语：拆成 TTS 好读的形式（按顺序替换，长的在前）
EN = [
    ("BasicTokenizer", "Basic Tokenizer"), ("RegexTokenizer", "Regex Tokenizer"), ("minbpe", "min B P E"),
    ("nanoGPT", "nano GPT"), ("<|endoftext|>", "end of text"), ("errors=\"replace\"", "errors 等于 replace"),
    ("float(\"inf\")", "正无穷"), ("_build_vocab", "build vocab"), ("vocab_size", "vocab size"),
    ("text_bytes", "text bytes"), ("get_stats", "get stats"), ("render_token", "render token"),
    ("nn.Embedding", "N N 点 Embedding"), ("PyTorch", "Py Torch"), ("tinyshakespeare", "tiny Shakespeare"),
    ("cross_entropy", "cross entropy"), ("get_batch", "get batch"), ("block_size", "block size"),
    ("batch_size", "batch size"), ("max_iters", "max iters"), ("eval_interval", "eval interval"),
    ("eval_iters", "eval iters"), ("max_new_tokens", "max new tokens"), ("estimate_loss", "estimate loss"),
    ("stoi", "S to I"), ("itos", "I to S"), ("CUDA", "C U D A"), ("no_grad", "no grad"),
    ("model.eval()", "model 点 eval"), ("model.train()", "model 点 train"), ("randint", "rand int"),
    ("UTF-8", "U T F 8"), ("set_to_none", "set to none"), ("Bigram", "Bigram"),
    ("Attention Is All You Need", "Attention is all you need"),
    ("GPT-2 small", "GPT 二 small"), ("GPT-2", "GPT 二"), ("GPT-3", "GPT 三"),
    ("Decoder-only", "Decoder only"), ("decoder-only", "Decoder only"),
    ("Pre-LN", "Pre L N"), ("Post-LN", "Post L N"),
    ("LayerNorm", "Layer Norm"), ("softmax", "soft max"), ("Softmax", "soft max"),
    ("one-hot", "one hot"), ("AdamW", "Adam W"), ("dropout", "drop out"),
    ("warmup", "warm up"), ("zero_grad()", "zero grad"), ("zero_grad", "zero grad"),
    ("backward()", "backward"), ("step()", "step"), ("lm_head", "LM head"),
    ("W_Q", "W Q"), ("W_K", "W K"), ("W_V", "W V"), ("W_O", "W O"),
    ("d_model", "D model"), ("d_k", "D K"), ("GELU", "G E L U"), ("ReLU", "R E L U"),
    ("logits", "logits"), ("logit", "logit"), ("Llama", "Llama"),
    ("ln ", "L N "), ("tokens", "token"),
]

# ---- 多音字：替换成同音且读音唯一的字（只影响朗读，不影响字幕）
POLY = [
    ("残差", "残插"), ("标准差", "标准插"), ("方差", "方插"), ("误差", "误插"),
    ("奇数", "基数"), ("累加", "垒加"), ("累积", "垒积"), ("学习率", "学习律"),
    ("当成", "看作"), ("当作", "看作"), ("分量", "元素"), ("调用", "掉用"), ("重叠", "虫叠"), ("还原", "环原"), ("重新", "虫新"), ("差距", "插距"),
]
XING = ["进行", "执行", "运行", "并行", "行为", "可行", "流行", "行动", "不行", "自行", "实行", "行走"]

DIG = "零一二三四五六七八九"


try:
    import config as _cfg
    EN = list(getattr(_cfg, "EXTRA_EN", [])) + EN
    POLY = list(getattr(_cfg, "EXTRA_POLY", [])) + POLY
except ImportError:
    pass


def int_cn(n):
    if n == 0:
        return "零"
    if n >= 100000000:
        hi, lo = divmod(n, 100000000)
        return int_cn(hi) + "亿" + (("零" if lo < 10000000 else "") + int_cn(lo) if lo else "")
    if n >= 10000:
        hi, lo = divmod(n, 10000)
        return int_cn(hi) + "万" + (("零" if lo < 1000 else "") + int_cn(lo) if lo else "")
    out, units, zero = "", ["千", "百", "十", ""], False
    for i, d in enumerate(f"{n:04d}"):
        d = int(d)
        if d == 0:
            zero = bool(out)
            continue
        if zero:
            out += "零"
            zero = False
        out += DIG[d] + units[i]
    if out.startswith("一十"):
        out = out[1:]
    return out


def num_cn(m):
    s = m.group(0)
    if "." in s:
        a, b = s.split(".")
        return int_cn(int(a)) + "点" + "".join(DIG[int(c)] for c in b)
    return int_cn(int(s))


def say(s):
    for a, b in EN:
        s = s.replace(a, b)
    for a, b in POLY:
        s = s.replace(a, b)
    # 行 → 航（行列的“行”），保留 xíng 的常见词
    keep = {}
    for i, w in enumerate(XING):
        tag = f"\x00{i}\x00"
        if w in s:
            s = s.replace(w, tag)
            keep[tag] = w
    s = s.replace("行", "航")
    for tag, w in keep.items():
        s = s.replace(tag, w)
    s = s.replace("=", " 等于 ").replace("×", " 乘 ").replace("≈", "约等于").replace("√", "根号").replace("%", "%")
    s = re.sub(r"(?<=[A-Za-z])\.(?=[A-Za-z])", " 点 ", s)
    s = s.replace("()", "").replace("_", " ")
    s = s.replace("“", "").replace("”", "").replace("《", "").replace("》", "")
    s = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"百分之\1", s)
    s = re.sub(r"(?<![\d.])2\s*(?=(次|个|轮|种|倍|位|条|张|层|份|段|行))", "两", s)
    s = re.sub(r"\d+(?:\.\d+)?", num_cn, s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", s)
    s = re.sub(r"\s+(?=[，。；：、！？])|(?<=[，。；：、！？])\s+", "", s)
    return s.strip()


if __name__ == "__main__":
    for x in ["GPT-2 small 有 12 个头，12×64 = 768", "50257 行，每行 768 个数", "约 1.24 亿", "按行做 softmax，并行计算",
              "残差连接", "3072", "1024", "10.8", "105", "1000000"]:
        print(x, "→", say(x))
