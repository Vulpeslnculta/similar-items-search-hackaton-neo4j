"""Multilingual vocabulary used by extraction.py and normalize.py.

Covers English, Danish, Swedish, Norwegian, German and Polish. Everything here is plain data -
extend it when a new site or language shows up; no code changes needed.
All entries are lowercase.
"""

# ---------- label -> canonical spec key ----------

LABEL_SYNONYMS = {
    "brand": ["brand", "brand name", "varemærke", "mærke", "mærkenavn", "märke", "varumärke", "merke", "merkenavn",
              "marke", "markenname", "marka", "make", "fabrikat", "label"],
    "manufacturer": ["manufacturer", "producent", "produsent", "hersteller", "fabrikant", "producer"],
    "model": ["model", "modell", "modèle", "modelo", "model number", "modelnummer", "modellnummer",
              "modelnr", "modelnr.", "numer modelu", "mpn", "herstellernummer", "part number",
              "producentens varenummer", "tillverkarens artikelnummer", "produsentens varenummer"],
    "gtin": ["ean", "upc", "gtin", "isbn", "ean/upc", "kod ean", "ean nummer", "ean-nummer", "ean-nr",
             "stregkode", "streckkod", "strekkode", "barcode", "ean-kod", "ean code"],
    "sku": ["sku", "id", "item id", "artikkelnr", "artikelnr", "artikkelnr.", "varenr", "varenr.", "varenummer", "artikelnummer", "artikkelnummer", "art.nr",
            "art.nr.", "artnr", "item number", "product code", "produktkode", "produktnummer", "item no"],
    "condition": ["condition", "stand", "varens stand", "stan", "zustand", "skick", "tilstand", "item condition"],
    "color": ["color", "colour", "farve", "farge", "färg", "farbe", "kolor", "produktfarve", "product colour",
              "product color", "shell colour", "colour name", "färgnamn", "farvenavn", "fargenavn"],
    "size": ["size", "størrelse", "storlek", "größe", "groesse", "rozmiar", "str", "str.", "taille",
             "størrelse (eu)", "size (eu)"],
    "material": ["material", "materials", "materiale", "materialer", "materiał", "composition",
                 "sammensætning", "materialsammansättning", "materiale (luv)", "ydre materiale", "yttertyg",
                 "ytre materiale", "outer material", "außenmaterial", "main material", "hovedmateriale",
                 "stof", "tyg", "stoff", "matriale", "materiaal", "materialsammensetning"],
    "lining": ["lining", "foder", "for", "fór", "innertyg", "futter", "innerfoder"],
    "upper": ["upper", "overdel", "ovandel", "överdel", "obermaterial"],
    "sole": ["sole", "sål", "yttersula", "ydersål", "sohle", "laufsohle", "outsole"],
    "gender": ["gender", "køn", "kön", "kjønn", "geschlecht", "płeć", "target group", "målgruppe",
               "kvinde / mand / barn", "department", "for hvem", "för vem"],
    "age": ["age", "alder", "ålder", "anbefalet alder", "age range", "age range (description)",
            "altersempfehlung", "wiek", "rekommenderad ålder", "anbefalt alder"],
    "fit": ["fit", "pasform", "passform"],
    "pattern": ["pattern", "mønster", "mönster", "muster", "wzór"],
    "type": ["type", "typ", "product type", "produkttype", "produkttyp", "typ produktu", "typ aparatu",
             "produktart", "rodzaj"],
    "style": ["style", "stil"],
    "season": ["season", "sæson", "säsong", "sesong", "saison"],
    "sleeve": ["sleeve length", "ærmelængde", "ärmlängd", "ermelengde", "ärmellänge", "ærmer"],
    "neckline": ["neckline", "halsudskæring", "halsringning", "halsrigning", "halsutringning", "ausschnitt"],
    "closure": ["closure", "lukning", "stängning", "lukking", "verschluss"],
    "heel": ["heel", "hæl", "klack", "absatz", "hælhøjde", "heel height"],
    "width": ["width", "bredde", "bredd", "breite", "szerokość"],
    "height": ["height", "højde", "höjd", "høyde", "höhe", "wysokość"],
    "length": ["length", "længde", "längd", "lengde", "länge", "długość", "length/depth", "längd/djup",
               "dybde", "djup", "depth", "tiefe", "dybde (cm)"],
    "dimensions": ["dimensions", "mål", "mått", "product dimensions", "abmessungen", "wymiary", "størrelse (cm)",
                   "dimensioner", "mål (cm)"],
    "weight": ["weight", "vægt", "vikt", "vekt", "gewicht", "waga", "item weight", "nettovægt", "nettovikt"],
    "volume": ["volume", "volumen", "indhold", "innehåll", "innhold", "inhalt", "pojemność", "kapacitet",
               "kapasitet", "capacity", "kapazität", "størrelse (ml)"],
    "storage": ["storage", "lagerplads", "lagring", "lagringskapacitet", "lagringskapasitet", "speicher",
                "speicherkapazität", "pamięć wbudowana", "hard drive", "harddisk", "storage capacity",
                "intern lagring", "internt minne"],
    "ram": ["ram", "memory", "arbejdshukommelse", "ram-hukommelse", "arbetsminne", "arbeidsminne",
            "arbeitsspeicher", "pamięć ram", "ram size"],
    "screen_size": ["screen size", "skærmstørrelse", "skärmstorlek", "skjermstørrelse", "bildschirmgröße",
                    "przekątna ekranu", "display size", "skærm", "skärm", "skjerm", "screen"],
    "processor": ["processor", "prozessor", "procesor", "cpu", "processortype", "processormodel"],
    "power": ["power", "effekt", "watt", "leistung", "moc", "strøm", "wattage", "maks. effekt"],
    "battery": ["battery", "batteri", "akku", "bateria", "battery capacity", "batterikapacitet", "batterikapasitet"],
    "voltage": ["voltage", "spænding", "spänning", "spenning", "spannung", "napięcie"],
    "connectivity": ["connectivity", "tilslutning", "anslutning", "tilkobling", "anschlüsse", "forbindelse"],
    "os": ["operating system", "styresystem", "operativsystem", "betriebssystem", "system operacyjny"],
    "skin_type": ["skin type", "hudtype", "hudtyp", "hauttyp", "typ skóry"],
    "hair_type": ["hair type", "hårtype", "hårtyp", "haartyp"],
    "scent": ["scent", "duft", "doft", "duftnote", "fragrance"],
    "spf": ["spf", "solbeskyttelsesfaktor", "solskyddsfaktor", "lichtschutzfaktor"],
    "pieces": ["number of pieces", "antal dele", "antal delar", "antall deler", "anzahl teile", "number of items",
               "antal varer", "antal enheder", "antal stk", "pack size", "antal", "pakkestørrelse"],
    "animal": ["dyr", "djurtyp", "animal", "tierart", "dyreart", "djur"],
    "format": ["format", "format filmu", "film format", "filmformat"],
    "focus": ["focus", "focus type", "ostrzenie", "typ ustawiania ostrości", "fokussierung"],
}
LABEL_TO_KEY = {syn: key for key, syns in LABEL_SYNONYMS.items() for syn in syns}

# Labels about the shop / sale / legal info, never product attributes.
IGNORED_LABELS = {
    "email", "e-mail", "mail", "tlf", "tlf.", "telefon", "phone", "telefonnr.", "telefonnummer", "sms/phone",
    "cvr", "cvr-nummer", "cvr nr", "cvr-nr", "org.nr", "org.nr.", "organisationsnummer", "vat", "vat no",
    "moms", "pris", "price", "regular price", "sale price", "cena", "cena przedmiotu", "address", "adresse",
    "adress", "postadresse", "postadress", "elektronisk adresse", "elektronisk adress", "tillverkare",
    "producent oplysninger", "kundeservice", "customer service", "menu", "find inspiration", "bli inspirerad",
    "express", "shopify", "note", "kategori", "category", "shipping", "delivery", "levering", "leveringstid",
    "fragt", "frakt", "versand", "wysyłka", "dostawa", "returns", "retur", "returnering", "zwroty",
    "location", "item location", "lokalisering", "lokalizacja", "handling time", "czas na wysłanie",
    "åbningstider", "öppettider", "åpningstider", "öffnungszeiten", "weekend", "helligdage",
    "mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag", "måndag", "tisdag", "lördag",
    "söndag", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "saturdays", "sundays",
    "seller notes", "uwagi sprzedaż", "uwagi sprzedawcy", "payments", "płatności", "zahlungsmethoden",
    "rücknahme", "artikelstandort", "name", "title", "status", "lagerstatus", "på lager", "description",
    "beskrivelse", "beskrivning", "rating", "anmeldelser", "reviews", "bh", "navn", "funktion",
    "kredit produkter", "farvekode", "fabrikantens navn", "produktionsland", "made in", "imported from",
}

# Values meaning "no brand".
NULL_BRANDS = {"diverse mærker", "diverse", "no brand", "unbranded", "generic", "ukendt", "okänd", "ukjent",
               "unknown", "various", "andre", "andra", "others", "n/a", "na", "none", "other", "andet", "övrigt", "øvrig", "brand"}

LEGAL_SUFFIXES = ["inc", "ltd", "llc", "corp", "corporation", "gmbh", "co", "s.a", "sa", "ag", "b.v", "bv",
                  "a/s", "aps", "ab", "as", "oy", "srl", "spa", "s.p.a", "sp. z o.o", "plc", "limited", "kg"]

BRAND_ALIASES = {
    "hewlett packard": "hp", "hewlett-packard": "hp", "samsung electronics": "samsung",
    "apple computer": "apple", "om system": "olympus", "hugo boss": "boss", "h&m": "h&m",
    "tommy hilfiger europe": "tommy hilfiger", "asics europe": "asics", "la rochere": "la rochère",
}

# ---------- value vocabularies ----------

COLORS = {
    "black": ["black", "sort", "svart", "schwarz", "czarny", "noir", "nero", "negro", "onyx", "jet"],
    "white": ["white", "hvid", "vit", "hvit", "weiß", "weiss", "biały", "blanc", "bianco", "offwhite",
              "off-white", "cream", "creme", "crème", "ecru", "ivory", "alabaster", "råhvid", "benhvid", "kremvit"],
    "grey": ["grey", "gray", "grå", "grau", "szary", "gris", "anthracite", "antracit", "charcoal", "melange"],
    "blue": ["blue", "blå", "blau", "niebieski", "bleu", "denim", "indigo", "turquoise", "turkis", "turkos", "petrol"],
    "navy": ["navy", "marine", "marineblå", "marinblå", "mørkeblå", "mörkblå", "dunkelblau", "granatowy"],
    "red": ["red", "rød", "röd", "rød", "czerwony", "rouge", "bordeaux", "burgundy", "vinrød", "vinröd"],
    "green": ["green", "grøn", "grön", "grønn", "grün", "zielony", "vert", "olive", "oliven", "khaki",
              "army", "mint", "mynte", "salvie", "sage"],
    "yellow": ["yellow", "gul", "gelb", "żółty", "jaune", "mustard", "sennep", "senap"],
    "orange": ["orange", "pomarańczowy", "rust", "rost"],
    "pink": ["pink", "lyserød", "rosa", "różowy", "rose", "fuchsia", "blush"],
    "purple": ["purple", "lilla", "lila", "fioletowy", "violet", "lavender", "lavendel", "plum", "blomme"],
    "brown": ["brown", "brun", "braun", "brązowy", "marron", "cognac", "chocolate", "choko", "chokolade",
              "camel", "taupe", "mocha", "mokka", "tobacco"],
    "beige": ["beige", "beżowy", "sand", "nude", "natur", "natural", "stone"],
    "gold": ["gold", "guld", "złoty", "golden"],
    "silver": ["silver", "sølv", "silber", "srebrny", "chrome", "krom", "stål", "steel"],
    "multicolor": ["multicolor", "multicolour", "multi", "flerfarvet", "flerfärgad", "flerfarget", "mehrfarbig",
                   "wielokolorowy", "print", "mønstret"],
    "transparent": ["transparent", "klar", "clear", "gennemsigtig", "genomskinlig"],
}
# color words that must match a whole word (they're substrings of unrelated words)
COLOR_EXACT_ONLY = {"rot", "jet", "multi", "army", "rose", "klar", "print", "natur", "stone", "sand",
                    "marine", "rust", "mint", "steel", "stål"}

GENDERS = {
    "women": ["women", "womens", "women's", "woman", "female", "ladies", "dame", "damer", "kvinde", "kvinder",
              "dam", "kvinna", "kvinnor", "kvinne", "kvinner", "damen", "frauen", "kobiety", "damskie", "damski"],
    "men": ["men", "mens", "men's", "male", "herre", "herrer", "mand", "mænd", "herr", "män", "mann",
            "menn", "herren", "männer", "mężczyźni", "męskie", "męski"],
    "kids": ["kids", "kid", "children", "child", "junior", "børn", "barn", "kinder", "dzieci", "girls", "boys",
             "piger", "drenge", "flickor", "pojkar", "jenter", "gutter", "mädchen", "jungen", "baby", "teens"],
    "unisex": ["unisex"],
}

MATERIALS = {
    "cotton": ["cotton", "bomuld", "bomull", "baumwolle", "bawełna", "coton", "økologisk bomuld"],
    "polyester": ["polyester", "pes", "polyestere", "poliester"],
    "wool": ["wool", "uld", "ull", "wolle", "wełna", "merino", "merinould", "merinoull", "laine"],
    "cashmere": ["cashmere", "kashmir", "kaschmir", "kaszmir"],
    "leather": ["leather", "læder", "läder", "lær", "leder", "skóra", "cuir", "skind", "calfskin", "kalveskind"],
    "suede": ["suede", "ruskind", "mocka", "semsket", "wildleder", "zamsz"],
    "linen": ["linen", "hør", "linne", "lin", "leinen", "len"],
    "silk": ["silk", "silke", "siden", "seide", "jedwab"],
    "viscose": ["viscose", "viskose", "viskos", "wiskoza", "rayon"],
    "elastane": ["elastane", "elastan", "spandex", "lycra", "elasthan"],
    "polyamide": ["polyamide", "polyamid", "nylon", "poliamid"],
    "acrylic": ["acrylic", "akryl", "acryl", "akryl"],
    "lyocell": ["lyocell", "tencel"],
    "modal": ["modal"],
    "down": ["down", "dun", "daunen", "puch"],
    "denim": ["denim"],
    "synthetic": ["synthetic", "syntet", "syntetisk", "synthetik", "kunststoff", "imiteret læder", "pu"],
    "rubber": ["rubber", "gummi", "kautschuk", "guma"],
    "textile": ["textile", "tekstil", "textil", "tkanina"],
    "plastic": ["plastic", "plast", "plastik", "polypropylene", "polypropylen", "pp", "abs", "polystyrene"],
    "metal": ["metal", "metall"],
    "stainless steel": ["stainless steel", "rustfrit stål", "rostfritt stål", "rustfritt stål", "edelstahl",
                        "stal nierdzewna", "stainless"],
    "aluminium": ["aluminium", "aluminum", "alu"],
    "glass": ["glass", "glas", "szkło"],
    "wood": ["wood", "træ", "trä", "tre", "holz", "drewno", "eg", "ek", "eik", "oak", "bøg", "fyr", "teak"],
    "bamboo": ["bamboo", "bambus", "bambu"],
    "ceramic": ["ceramic", "keramik", "keramikk", "ceramika", "porcelæn", "porslin", "porselen", "stoneware",
                "stentøj", "stengods"],
    "silicone": ["silicone", "silikone", "silikon"],
    "paper": ["paper", "papir", "papper", "papier", "karton", "cardboard", "pap"],
    "gold": ["18 kt. guld", "14 kt. guld", "guld", "gold"],
    "silver": ["sterling silver", "sterlingsølv", "sølv", "silver"],
}
MATERIAL_EXACT_ONLY = {"lin", "len", "dun", "down", "pes", "pu", "pp", "abs", "eg", "ek", "tre", "pap", "alu",
                       "gold", "guld", "silver", "sølv", "modal", "metal", "plast"}

# ---------- departments (top-level taxonomy) ----------
# kw: keywords matched as whole words, or as the last part of a compound word ("vinterjakke" -> "jakke")
#     when >= 4 chars; prefix "=" means whole-word only.
# about: short description used for the embedding fallback when no keyword matches.
DEPARTMENTS = {
    "clothing": {
        "about": "clothing apparel garments: t-shirt, shirt, sweater, jeans, trousers, dress, jacket, coat, "
                 "skirt, underwear, socks, swimwear, tøj, kläder, klær, kleidung",
        "kw": ["jean", "legging", "slipover", "trøjer", "kostume", "kostym", "cosplay", "dräkt", "dräkter", "clothing", "apparel", "tøj", "kläder", "klær", "kleidung", "odzież", "ubrania", "t-shirt",
               "tshirt", "t-shirts", "shirt", "skjorte", "skjorta", "hemd", "koszula", "sweater", "pullover",
               "hoodie", "sweatshirt", "trøje", "tröja", "genser", "jeans", "trousers", "pants", "bukser",
               "byxor", "bukse", "hose", "spodnie", "chinos", "dress", "kjole", "klänning", "sukienka", "kleid",
               "jacket", "jakke", "jacka", "jacke", "kurtka", "blazer", "coat", "frakke", "kappa", "kåpa",
               "mantel", "płaszcz", "parka", "vest", "skirt", "nederdel", "kjol", "skjørt", "rock", "spódnica",
               "shorts", "blouse", "bluse", "blus", "bluzka", "cardigan", "strik", "stickat", "=top", "toppe",
               "tops", "tank", "underwear", "undertøj", "underkläder", "unterwäsche", "bielizna", "trusser",
               "thong", "bh", "bra", "socks", "strømper", "strumpor", "sokker", "socken", "skarpetki",
               "swimwear", "badetøj", "badkläder", "badetøy", "bikini", "leggings", "tights", "body",
               "tracksuit", "joggers", "polo", "badrock", "badekåbe", "morgenkåbe", "pyjamas", "nattøj",
               "overall", "romper", "jumpsuit", "flyverdragt", "regntøj", "fleece", "uniform", "arbejdstøj",
               "arbetskläder", "workwear"],
    },
    "footwear": {
        "about": "footwear shoes: sneakers, boots, sandals, heels, slippers, sko, skor, schuhe",
        "kw": ["footwear", "shoes", "=sko", "skor", "schuhe", "buty", "sneakers", "trainers", "boots",
               "støvler", "stövlar", "støvletter", "støvletter", "stiefel", "ankelstøvler", "sandals", "sandaler",
               "sandalen", "clogs", "træsko", "tøfler", "tofflor", "slippers", "hjemmesko", "heels", "pumps",
               "loafers", "ballerinas", "løbesko", "löparskor", "gummistøvler", "vinterstøvler", "sneaker",
               "sandal", "snørestøvletter", "støvle", "flip-flops", "klipklapper"],
    },
    "bags & accessories": {
        "about": "bags and fashion accessories: handbag, backpack, wallet, belt, hat, cap, scarf, gloves, "
                 "sunglasses, umbrella",
        "kw": ["bag", "bags", "taske", "tasker", "väska", "väskor", "veske", "tasche", "torebka", "handbag",
               "backpack", "rygsæk", "ryggsäck", "ryggsekk", "rucksack", "plecak", "wallet", "pung", "plånbok",
               "lommebok", "geldbörse", "portfel", "belt", "bælte", "bälte", "belte", "gürtel", "pasek",
               "=hat", "hue", "mössa", "lue", "mütze", "czapka", "cap", "kasket", "keps", "beanie", "scarf",
               "tørklæde", "halstørklæde", "halsduk", "skjerf", "schal", "szalik", "gloves", "handsker",
               "handskar", "hansker", "handschuhe", "rękawiczki", "vanter", "sunglasses", "solbriller",
               "solglasögon", "sonnenbrille", "umbrella", "paraply", "regnskærm", "accessories", "tilbehør",
               "accessoarer", "bæltetaske", "toilettaske", "kuffert", "resväska", "koffert", "suitcase"],
    },
    "jewelry & watches": {
        "about": "jewelry and watches: ring, necklace, earrings, bracelet, wristwatch, smykker, smycken",
        "kw": ["jewelry", "jewellery", "smykker", "smycken", "smykke", "schmuck", "biżuteria", "=ring", "ringe",
               "necklace", "halskæde", "halsband", "halskjede", "halskette", "naszyjnik", "earrings",
               "øreringe", "örhängen", "øredobber", "ohrringe", "kolczyki", "earsticks", "ørestikker",
               "bracelet", "armbånd", "armband", "bransoletka", "pendant", "vedhæng", "hänge", "anheng",
               "watch", "watches", "armbåndsur", "armbandsur", "klokke", "uhr", "zegarek", "smartwatch"],
    },
    "beauty & personal care": {
        "about": "beauty cosmetics and personal care: makeup, skincare, perfume, shampoo, cream, serum, "
                 "nail polish, deodorant, kosmetik, hudpleje",
        "kw": ["bomullspinnar", "vatpinde", "q-tips", "bronzer", "lip oil", "læbepomade", "otoskop", "øreskyder", "personlig pleje", "hygiejne", "hygien", "lommetørklæder", "brow", "øjenbryn", "eyeliner", "eyeshadow", "øjenskygge", "pudder", "eye care", "øjencreme", "collagen", "anti-wrinkle", "rynkecreme", "hudcreme", "beauty", "cosmetics", "kosmetik", "kosmetyki", "kosmetikk", "makeup", "make-up", "sminke",
               "smink", "skincare", "hudpleje", "hudvård", "hudpleie", "hautpflege", "pielęgnacja", "perfume",
               "parfume", "parfym", "parfum", "perfumy", "eau de toilette", "eau de parfum", "shampoo",
               "schampo", "sjampo", "szampon", "conditioner", "balsam", "serum", "creme", "kräm", "krem",
               "cream", "lotion", "lipstick", "læbestift", "läppstift", "leppestift", "mascara", "foundation",
               "concealer", "neglelak", "nagellack", "neglelakk", "nail polish", "deodorant", "hårpleje",
               "hårvård", "hårpleie", "haarpflege", "makeupbørster", "makeup brush", "pudder",
               "toothpaste", "tandpasta", "barbering", "rakning", "shaving", "sunscreen", "solcreme",
               "solkräm", "bodylotion", "duft"],
    },
    "health": {
        "about": "health and wellbeing: vitamins, supplements, pharmacy, first aid, medical devices",
        "kw": ["health", "sundhed", "hälsa", "helse", "gesundheit", "zdrowie", "pharmacy", "apotek",
               "apotheke", "apteka", "vitamins", "vitaminer", "kosttilskud", "kosttillskott", "supplement",
               "kosttilskudd", "first aid", "førstehjælp", "plaster", "termometer", "thermometer",
               "blodtryksmåler", "massage"],
    },
    "phones & tablets": {
        "about": "mobile phones, smartphones, tablets and phone accessories: charger, phone case, cable",
        "kw": ["etui", "mobiletui", "flip etui", "galaxy", "tab s9", "skærmbeskytter", "smartphone", "mobile phone", "mobiltelefon", "mobiltelefoner", "telefon", "handy", "iphone",
               "tablet", "ipad", "phone case", "mobilcover", "mobilskal", "cover", "charger", "oplader",
               "laddare", "lader", "ladegerät", "ładowarka", "supervooc", "powerbank", "power bank",
               "skærmbeskyttelse", "skärmskydd"],
    },
    "computers": {
        "about": "computers and IT: laptop, desktop pc, monitor, keyboard, mouse, printer, ssd, router",
        "kw": ["gaming tastatur", "case cooler", "case fan", "blæser", "rtx", "geforce", "radeon", "computer", "computere", "dator", "datamaskin", "laptop", "bærbar", "notebook", "macbook",
               "=pc", "desktop", "monitor", "skærm", "bildskärm", "skjerm", "keyboard", "tastatur",
               "=mus", "mouse", "maus", "ssd", "harddisk", "hårddisk", "router", "printer", "skrivare",
               "drucker", "toner", "blæk", "bläck", "grafikkort", "graphics card", "processor", "bundkort",
               "usb", "webcam", "headset", "laserprinter", "laserpapir", "printerpapir"],
    },
    "cameras & photo": {
        "about": "cameras and photography: digital camera, film camera, lens, tripod, slr, mirrorless",
        "kw": ["softbox", "fotostudio", "blitz", "speedlite", "godox", "camera", "cameras", "kamera", "kameraer", "aparat", "fotografia", "lens", "objektiv",
               "obiektyw", "dslr", "slr", "mirrorless", "spejlrefleks", "systemkamera", "lustrzanka",
               "tripod", "stativ", "film camera", "analog camera", "actioncam", "gopro"],
    },
    "electronics": {
        "about": "consumer electronics: tv, headphones, speakers, gaming consoles, smart home, cables, batteries",
        "kw": ["videospil", "datorspel", "dataspill", "pc game", "steam", "gaming-tilbehør", "rat", "adapter", "strømstik", "stikkontakt", "electronics", "elektronik", "elektronikk", "=tv", "television", "fjernsyn", "headphones",
               "hovedtelefoner", "hörlurar", "hodetelefoner", "kopfhörer", "słuchawki", "earbuds", "speaker",
               "højttaler", "högtalare", "høyttaler", "lautsprecher", "głośnik", "soundbar", "console",
               "playstation", "xbox", "nintendo", "gaming", "kabel", "cable", "battery", "batteri", "batterier",
               "smart home", "drone", "projector", "projektor", "radio", "mixer", "forstærker", "amplifier",
               "guitar", "guitarer", "mikrofon", "microphone", "=led"],
    },
    "home & furniture": {
        "about": "home, furniture and decor: sofa, chair, table, lamp, rug, curtains, bedding, pillows, "
                 "candles, vases, storage, christmas decorations",
        "kw": ["bedspread", "sengetæppe", "överkast", "sengeteppe", "örngott", "pudebetræk", "lænestol", "fåtölj", "lenestol", "sengebord", "seng", "senge", "säng", "wall light", "væglampe", "loftslampe", "taklampa", "etagere", "skilteholder", "pyntepuder", "pudebetræk", "lysestage", "lysestager", "ljusstake", "lysestake", "kerzenständer", "magnet", "køleskabsmagnet", "ophæng", "juleophæng", "julekugler", "furniture", "møbler", "möbler", "möbel", "meble", "sofa", "soffa", "chair", "=stol",
               "stolar", "stuhl", "krzesło", "table", "=bord", "tisch", "stół", "lamp", "lampe", "lampa",
               "belysning", "rug", "tæppe", "tæpper", "matta", "teppe", "teppich", "dywan", "curtain",
               "gardin", "gardiner", "bedding", "sengetøj", "sängkläder", "sengetøy", "pillow", "pude",
               "kudde", "pute", "kissen", "poduszka", "decor", "dekoration", "dekor", "julepynt", "juledekoration",
               "julefigurer", "candle", "stearinlys", "ljus", "kerze", "świeca", "vase", "towel", "håndklæde",
               "handduk", "håndkle", "plaid", "blanket", "tæppe", "filt", "shelf", "hylde", "hylla", "reol",
               "byrå", "kommode", "skab", "skåp", "skap", "storage", "opbevaring", "förvaring", "oppbevaring",
               "frame", "frames", "ramme", "rammer", "poster", "plakat", "spejl", "spegel", "speil", "mirror", "hem", "hjem",
               "home", "bolig", "boligtilbehør", "nisser", "nissedør", "støvsugerposer", "vacuum", "støvsuger",
               "dammsugare", "vaskemiddel", "rengøring", "städ", "parasol"],
    },
    "kitchen & dining": {
        "about": "kitchen and dining: pans, pots, knives, plates, glasses, mugs, coffee makers, kettles, "
                 "blenders, kitchen storage",
        "kw": ["serviet", "servietter", "servietring", "servetter", "tallerkenlåg", "låg", "kitchen", "køkken", "kök", "kjøkken", "küche", "kuchnia", "pan", "pande", "stegepande",
               "stegepander", "stekpanna", "gryde", "kastrull", "topf", "garnek", "knife", "kniv", "knive",
               "messer", "nóż", "plate", "tallerken", "tallrik", "skål", "skåle", "bowl", "glas", "glass",
               "mug", "krus", "mugg", "kop", "kopp", "spisestel", "servise", "bestik", "cutlery", "kettle",
               "elkedel", "vattenkokare", "vannkoker", "wasserkocher", "blender", "stavblender", "mixer",
               "kaffemaskine", "kaffebryggare", "coffee maker", "espresso", "køkkenopbevaring", "pizzasæt",
               "bagning", "bakning", "baking", "kaffefilter", "målesett", "måleske", "smørklokke", "vinglas",
               "dessertskål", "airfryer"],
    },
    "tools & garden": {
        "about": "tools, DIY, hardware and garden: drills, screwdrivers, locks, garden tools, plants, "
                 "lawn mower, outdoor heating, heat pumps",
        "kw": ["svejseapparat", "svejseapparater", "tigsvets", "svetsaggregat", "græsmaskiner", "skårlægger", "kildeskifter", "klæbesøm", "værktøjskasse", "elektriker", "elektrikertape", "isoleringstape", "vægmaling", "maling", "tools", "værktøj", "verktyg", "verktøy", "werkzeug", "narzędzia", "drill", "boremaskine",
               "borrmaskin", "bohrmaschine", "wiertarka", "screwdriver", "skruetrækker", "hammer", "garden",
               "trädgård", "hage", "garten", "ogród", "haveredskaber", "plant", "planter", "växt", "växter",
               "pflanze", "roślina", "plæneklipper", "gräsklippare", "gressklipper", "lawn mower", "lås",
               "låse", "låsekasse", "låsekasser", "byggemarked", "bygg", "maling", "färg", "hegnsklipper",
               "hækkeklipper", "grenknuser", "kompostkværn", "varmepumpe", "varmepumpe/klimaanlæg",
               "heat pump", "aircondition", "grangrene", "blomster", "frø", "fröer", "gødning"],
    },
    "baby & toys": {
        "about": "baby gear, kids and toys: stroller, baby bottle, diapers, toys, lego, dolls, puzzles, "
                 "board games, plush, fidget toys",
        "kw": ["magic the gathering", "prerelease", "booster", "enkeltkort", "spejl til bil", "babyspejl", "magic cube", "rubiks", "pokémonkort", "pokemon", "pokémon", "samlekort", "funko", "actionfigur", "figur", "figure", "collectible", "montessori", "babyudstyr", "baby udstyr", "stroller", "barnevogn", "barnvagn", "kinderwagen",
               "wózek", "klapvogn", "diaper", "bleer", "blöjor", "bleier", "windeln", "pacifier", "sut",
               "napp", "sutteflaske", "nappflaska", "toy", "toys", "legetøj", "leksaker", "leker", "leketøy",
               "spielzeug", "zabawki", "lego", "duplo", "puzzle", "puslespil", "pussel", "doll", "dukke",
               "docka", "dukker", "bamse", "plush", "plys", "board game", "brætspil", "sällskapsspel",
               "brettspill", "kaleidoskop", "squishy", "fidget", "needoh", "skiftepude", "changing pad",
               "sugekop", "suction plate", "barnestol", "højstol", "babytilbehør", "eventyrsett", "lekesett",
               "sorting set", "toploaders", "trading cards", "samlekort"],
    },
    "sports & outdoor": {
        "about": "sports, fitness and outdoor: running, training, cycling, camping, skiing, golf, football, "
                 "treadmill, tents, hiking, horse riding equipment",
        "kw": ["snorkel", "snorkelsæt", "dykning", "dykke", "diving", "svømning", "simning", "swimming", "freeski", "skisæt", "skistøvler", "skidor", "løbetights", "sport", "sports", "sportswear", "outdoor", "fitness", "training", "træning", "träning",
               "trening", "running", "løb", "löpning", "bicycle", "cykel", "cykler", "sykkel", "fahrrad",
               "rower", "wheelset", "hjulsæt", "camping", "tent", "telt", "tält", "zelt", "=ski", "skiing",
               "golf", "driver", "football", "fodbold", "fotboll", "fotball", "yoga", "hiking", "vandring",
               "löpband", "løbebånd", "treadmill", "motionscykel", "kettlebell", "håndvægte", "hantlar",
               "vintersport", "ridning", "riding", "hest", "häst", "horse", "dækken", "padel", "tennis",
               "badminton", "fiskeri", "fiske", "fishing", "jagt", "jakt", "våben", "riffelkuffert", "skydning"],
    },
    "books & media": {
        "about": "books, music and media: novels, non-fiction, audiobooks, vinyl records, cds, dvds, "
                 "magazines, comics",
        "kw": ["book", "books", "=bog", "bøger", "=bok", "böcker", "bøker", "buch", "bücher", "książka",
               "novel", "roman", "ebook", "e-bog", "audiobook", "lydbog", "ljudbok", "lydbok", "hörbuch",
               "vinyl", "=lp", "=cd", "=dvd", "blu-ray", "magazine", "tegneserie", "serietidning",
               "comic", "myths", "paperback", "hardback", "indbundet", "inbunden"],
    },
    "office & stationery": {
        "about": "office supplies and stationery: pens, paper, calendars, notebooks, binders, labels, "
                 "name badges, printer paper",
        "kw": ["office", "kontor", "kontorartikler", "kontorsmaterial", "büro", "biuro", "pen", "kuglepen",
               "penna", "kulepenn", "stift", "kugelschreiber", "długopis", "paper", "papir", "papper",
               "notebook", "notesbog", "anteckningsbok", "notatbok", "calendar", "kalender", "kalendarz",
               "dagskalender", "binder", "ringbind", "pärm", "label", "etiket", "etiketter", "navneskilt",
               "navneskilte", "visitkort", "stationery", "papirvarer", "kuvert", "envelope", "lamineringslommer",
               "laminating", "tape", "hæftemaskine", "häftapparat", "whiteboard"],
    },
    "automotive": {
        "about": "car parts and automotive: brake pads, filters, tyres, wheels, rims, shock absorbers, "
                 "wipers, motor oil, car accessories",
        "kw": ["car", "bil", "auto", "samochód", "car parts", "bildele", "bildelar", "reservedele",
               "autoteile", "brake", "bremse", "bremser", "broms", "bromsar", "bremsbelag", "bremseklodser",
               "oil filter", "oliefilter", "oljefilter", "luftfilter", "tire", "tyre", "dæk", "däck", "dekk",
               "reifen", "opona", "fælge", "fælg", "fälg", "felg", "felgen", "rims", "alufælge", "wiper",
               "viskerblade", "torkarblad", "vindusvisker", "spark plug", "tændrør", "tändstift", "motorolie",
               "motorolja", "motorolje", "motor oil", "støddæmper", "stötdämpare", "støtdemper", "stoßdämpfer",
               "shock absorber", "udstødning", "avgassystem", "koblingssæt", "kopplingssats", "japan racing",
               "bremseskive", "bromsskiva"],
    },
    "food & drinks": {
        "about": "food and drinks: candy, chocolate, snacks, coffee, tea, soda, wine, groceries, baking "
                 "ingredients",
        "kw": ["rødvin", "hvidvin", "rosévin", "rødvine", "riesling", "barbaresco", "barolo", "chianti", "champagne", "prosecco", "cava", "whisky", "whiskey", "=gin", "=rom", "vodka", "spaghetti", "pasta", "=ris", "müsli", "granola", "chokoladebar", "sour", "gummies", "chews", "mejeri", "mejeriprodukter", "=ost", "ostar", "æg", "flager", "vingummi", "food", "=mad", "lebensmittel", "żywność", "dagligvarer", "matvaror", "candy", "slik",
               "godis", "godteri", "süßigkeiten", "słodycze", "chocolate", "chokolade", "choklad", "sjokolade",
               "schokolade", "czekolada", "snack", "snacks", "chips", "coffee beans", "kaffebønner", "kaffe",
               "tea", "=te", "tee", "herbata", "soda", "sodavand", "läsk", "brus", "juice", "wine", "vin",
               "øl", "öl", "beer", "spiritus", "skittles", "smarties", "glitter dust", "bagepulver", "mel",
               "krydderier", "kryddor", "sirup", "lakrids", "lakrits", "marmelade", "honning", "honung"],
    },
    "pets": {
        "about": "pet supplies: dog food, cat food, cat litter, leashes, bird and aquarium supplies, "
                 "dog treats",
        "kw": ["høns", "hønsehus", "kattebakke", "hundeleker", "hundelegetøj", "kattelegetøj", "kosedyr til hund", "pet", "pets", "kæledyr", "husdjur", "kjæledyr", "haustier", "zwierzęta", "dog", "=hund",
               "hunde", "hundar", "pies", "=cat", "=kat", "katte", "=katt", "katter", "katze", "=kot",
               "litter", "kattegrus", "kattsand", "foder", "hundefoder", "kattefoder", "fôr", "futter",
               "karma", "torrfoder", "aquarium", "akvarium", "fugl", "fågel", "papegøje", "papegøjer",
               "siddepind", "snor", "halsbånd", "koppel", "hvalp", "valp", "tyggeben", "godbidder",
               "litter boxes", "kattebakke"],
    },
    "hobby & crafts": {
        "about": "hobby, crafts and sewing: yarn, knitting patterns, fabric, sewing, ribbons, beads, "
                 "paint, drawing, model kits, trading card supplies",
        "kw": ["hobby", "crafts", "håndarbejde", "handarbete", "håndarbeid", "basteln", "yarn", "garn",
               "garner", "wolle", "knitting", "strikning", "stickning", "strikking", "strikkeopskrift",
               "opskrifter", "opskrift", "pattern", "mønster", "knitting pattern", "fabric", "stof", "tyg",
               "sewing", "syning", "sömnad", "søm", "bånd", "snor", "lidse", "perler", "pärlor", "beads",
               "maling", "akvarel", "tegning", "drawing", "kreativ", "patchwork", "kidmohair", "mohair",
               "broderi", "embroidery", "hæklet", "hækling", "virkning"],
    },
    "travel & experiences": {
        "about": "travel and experiences: tours, tickets, activities, excursions, museum entry, gift "
                 "experiences",
        "kw": ["tour", "tours", "ticket", "tickets", "billet", "billetter", "biljett", "biljetter", "experience",
               "oplevelse", "oplevelser", "upplevelse", "opplevelse", "erlebnis", "excursion", "udflugt",
               "utflykt", "activity", "aktivitet", "museum", "guided", "sightseeing", "cruise", "hotel",
               "rejse", "resa", "reise", "gavekort", "presentkort", "gift card"],
    },
}

# ---------- similarity weights ----------
# Weight of a shared attribute in weighted-Jaccard similarity (GDS) and in hybrid ranking.
SPEC_WEIGHTS = {
    "type": 2.0, "material": 1.2, "upper": 1.0, "color": 1.0, "gender": 1.5, "age": 1.0, "fit": 0.8,
    "pattern": 0.6, "style": 0.8, "season": 0.6, "sleeve": 0.6, "neckline": 0.5, "heel": 0.6,
    "storage": 1.5, "ram": 1.5, "screen_size": 1.5, "processor": 1.5, "os": 1.0, "format": 1.5,
    "focus": 0.8, "volume": 1.2, "weight": 0.5, "power": 1.0, "skin_type": 1.2, "hair_type": 1.2,
    "scent": 1.0, "spf": 1.0, "animal": 1.5, "size": 0.2, "dimensions": 0.4, "width": 0.4,
    "height": 0.4, "length": 0.4, "pieces": 0.5, "condition": 0.5, "lining": 0.4, "sole": 0.4,
}
DEFAULT_SPEC_WEIGHT = 0.6
REL_WEIGHTS = {"OF_MODEL": 6.0, "MADE_BY": 3.0, "IN_CATEGORY": 2.0}
