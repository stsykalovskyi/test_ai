"""Domain constants for Ukrainian morphology support."""

CASES = {
    "називний": "nomn",
    "родовий": "gent",
    "давальний": "datv",
    "знахідний": "accs",
    "орудний": "ablt",
    "місцевий": "loct",
    "кличний": "voct",
}

CASE_ALIASES = {
    "наз": "називний",
    "род": "родовий",
    "дав": "давальний",
    "знах": "знахідний",
    "оруд": "орудний",
    "місц": "місцевий",
    "клич": "кличний",
    "nom": "називний",
    "gen": "родовий",
    "dat": "давальний",
    "acc": "знахідний",
    "ins": "орудний",
    "loc": "місцевий",
    "voc": "кличний",
}

GENDERS = {"masculine", "feminine", "neuter"}
ANIMACY = {"animate", "inanimate"}
