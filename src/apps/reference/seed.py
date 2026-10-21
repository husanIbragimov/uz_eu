"""Reference seed data: sectors, EU-27 countries, Uzbekistan regions/districts, organizations, main-task template.

`seed_reference_data(apps)` is idempotent and takes an app registry so it can run both from a data
migration (historical models) and from the `seed_reference_data` management command (live models).
"""

SECTORS = [
    "Energy",
    "Renewable Energy",
    "Transport & Logistics",
    "Water Supply & Sanitation",
    "Agriculture & Food Processing",
    "Industry & Manufacturing",
    "Construction Materials",
    "Mining & Metallurgy",
    "Healthcare",
    "Education",
    "Digital & ICT",
    "Tourism",
    "Finance & SMEs",
    "Environment & Climate",
    "Urban Development",
]

EU_COUNTRIES = [
    ("Austria", "AT"),
    ("Belgium", "BE"),
    ("Bulgaria", "BG"),
    ("Croatia", "HR"),
    ("Cyprus", "CY"),
    ("Czechia", "CZ"),
    ("Denmark", "DK"),
    ("Estonia", "EE"),
    ("Finland", "FI"),
    ("France", "FR"),
    ("Germany", "DE"),
    ("Greece", "GR"),
    ("Hungary", "HU"),
    ("Ireland", "IE"),
    ("Italy", "IT"),
    ("Latvia", "LV"),
    ("Lithuania", "LT"),
    ("Luxembourg", "LU"),
    ("Malta", "MT"),
    ("Netherlands", "NL"),
    ("Poland", "PL"),
    ("Portugal", "PT"),
    ("Romania", "RO"),
    ("Slovakia", "SK"),
    ("Slovenia", "SI"),
    ("Spain", "ES"),
    ("Sweden", "SE"),
]

# Region -> districts (district-level administrative units and cities of regional subordination).
UZ_REGIONS = {
    "Republic of Karakalpakstan": [
        "Amudarya",
        "Beruniy",
        "Bozatau",
        "Chimbay",
        "Ellikkala",
        "Kanlikul",
        "Karauzyak",
        "Kegeyli",
        "Khodjeyli",
        "Kungrad",
        "Muynak",
        "Nukus",
        "Nukus city",
        "Shumanay",
        "Takhiatash",
        "Takhtakupir",
        "Turtkul",
    ],
    "Andijan region": [
        "Andijan",
        "Andijan city",
        "Asaka",
        "Baliqchi",
        "Bo'ston",
        "Bulakbashi",
        "Izboskan",
        "Jalaquduq",
        "Khanabad city",
        "Khodjaabad",
        "Kurgontepa",
        "Markhamat",
        "Oltinkul",
        "Pakhtaabad",
        "Shakhrikhan",
        "Ulugnor",
    ],
    "Bukhara region": [
        "Alat",
        "Bukhara",
        "Bukhara city",
        "Gijduvan",
        "Jondor",
        "Kagan",
        "Kagan city",
        "Karakul",
        "Karaulbazar",
        "Peshku",
        "Romitan",
        "Shafirkan",
        "Vabkent",
    ],
    "Fergana region": [
        "Altiarik",
        "Bagdad",
        "Beshariq",
        "Buvayda",
        "Dangara",
        "Fergana",
        "Fergana city",
        "Furqat",
        "Kokand city",
        "Kushtepa",
        "Kuva",
        "Kuvasay city",
        "Margilan city",
        "Rishtan",
        "Sokh",
        "Tashlak",
        "Uchkuprik",
        "Uzbekistan",
        "Yazyavan",
    ],
    "Jizzakh region": [
        "Arnasay",
        "Bakhmal",
        "Dustlik",
        "Forish",
        "Gallaaral",
        "Jizzakh city",
        "Mirzachul",
        "Pakhtakor",
        "Sharof Rashidov",
        "Yangiabad",
        "Zaamin",
        "Zafarabad",
        "Zarbdar",
    ],
    "Kashkadarya region": [
        "Chiroqchi",
        "Dehkanabad",
        "Guzar",
        "Kamashi",
        "Karshi",
        "Karshi city",
        "Kasan",
        "Kasbi",
        "Kitab",
        "Kukdala",
        "Mirishkor",
        "Mubarek",
        "Nishan",
        "Shakhrisabz",
        "Shakhrisabz city",
        "Yakkabag",
    ],
    "Khorezm region": [
        "Bagat",
        "Gurlen",
        "Khanka",
        "Khazarasp",
        "Khiva",
        "Khiva city",
        "Kushkupir",
        "Shavat",
        "Tuprakkala",
        "Urgench",
        "Urgench city",
        "Yangiarik",
        "Yangibazar",
    ],
    "Namangan region": [
        "Chartak",
        "Chust",
        "Davlatabad",
        "Kasansay",
        "Mingbulak",
        "Namangan",
        "Namangan city",
        "Naryn",
        "Pap",
        "Turakurgan",
        "Uchkurgan",
        "Uychi",
        "Yangikurgan",
    ],
    "Navoi region": [
        "Kanimekh",
        "Karmana",
        "Khatyrchi",
        "Kyzyltepa",
        "Navbahor",
        "Navoi city",
        "Nurata",
        "Tamdy",
        "Uchkuduk",
        "Zarafshan city",
    ],
    "Samarkand region": [
        "Akdarya",
        "Bulungur",
        "Ishtikhan",
        "Jambay",
        "Kattakurgan",
        "Kattakurgan city",
        "Koshrabot",
        "Narpay",
        "Nurabad",
        "Pakhtachi",
        "Pastdargom",
        "Payarik",
        "Samarkand",
        "Samarkand city",
        "Tayloq",
        "Urgut",
    ],
    "Surkhandarya region": [
        "Angor",
        "Bandikhon",
        "Baysun",
        "Denau",
        "Jarkurgan",
        "Kizirik",
        "Kumkurgan",
        "Muzrabot",
        "Oltinsoy",
        "Sariasiya",
        "Sherabad",
        "Shurchi",
        "Termez",
        "Termez city",
        "Uzun",
    ],
    "Syrdarya region": [
        "Akaltyn",
        "Bayaut",
        "Gulistan",
        "Gulistan city",
        "Khavast",
        "Mekhnatabad",
        "Mirzaabad",
        "Sardoba",
        "Sayhunabad",
        "Shirin city",
        "Syrdarya",
        "Yangiyer city",
    ],
    "Tashkent region": [
        "Akhangaran",
        "Akhangaran city",
        "Akkurgan",
        "Almalyk city",
        "Angren city",
        "Bekabad",
        "Bekabad city",
        "Bostanlyk",
        "Buka",
        "Chinaz",
        "Chirchik city",
        "Kibray",
        "Kuyichirchik",
        "Nurafshon city",
        "Parkent",
        "Pskent",
        "Tashkent",
        "Urtachirchik",
        "Yangiyul",
        "Yangiyul city",
        "Yukorichirchik",
        "Zangiata",
    ],
    "Tashkent city": [
        "Bektemir",
        "Chilanzar",
        "Mirabad",
        "Mirzo Ulugbek",
        "Olmazor",
        "Sergeli",
        "Shaykhantakhur",
        "Uchtepa",
        "Yakkasaray",
        "Yangihayot",
        "Yashnabad",
        "Yunusabad",
    ],
}

ORGANIZATIONS = {
    "eu": [
        "European Investment Bank (EIB)",
        "KfW Development Bank",
        "European Bank for Reconstruction and Development (EBRD)",
        "Agence Française de Développement (AFD)",
        "European Commission (DG INTPA)",
        "Cassa Depositi e Prestiti (CDP)",
    ],
    "uz": [
        "Ministry of Investment, Industry and Trade",
        "Ministry of Economy and Finance",
        "Ministry of Energy",
        "Ministry of Transport",
        "Ministry of Agriculture",
        "Ministry of Water Resources",
        "Ministry of Health",
        "Ministry of Construction and Housing and Communal Services",
        "Uzbekcement JSC",
    ],
}

MAIN_TASK_TEMPLATE = [
    "Negotiations",
    "Project documentation",
    "Land preparation",
    "Financing status",
    "Permits",
    "Construction works",
    "External engineering infrastructure",
    "Equipment supply",
    "Equipment installation",
    "Project launch",
]


def seed_reference_data(apps) -> dict[str, int]:
    Sector = apps.get_model("reference", "Sector")
    Country = apps.get_model("reference", "Country")
    Region = apps.get_model("reference", "Region")
    Organization = apps.get_model("reference", "Organization")
    MainTaskTemplate = apps.get_model("reference", "MainTaskTemplate")

    created = {"sectors": 0, "countries": 0, "regions": 0, "districts": 0, "organizations": 0, "templates": 0}

    for position, name in enumerate(SECTORS, start=1):
        _, is_new = Sector.objects.get_or_create(name=name, defaults={"position": position})
        created["sectors"] += is_new

    for name, iso_code in EU_COUNTRIES:
        _, is_new = Country.objects.get_or_create(iso_code=iso_code, defaults={"name": name, "is_eu_member": True})
        created["countries"] += is_new

    for position, (region_name, districts) in enumerate(UZ_REGIONS.items(), start=1):
        region, is_new = Region.objects.get_or_create(parent=None, name=region_name, defaults={"position": position})
        created["regions"] += is_new
        for district_name in districts:
            _, is_new = Region.objects.get_or_create(parent=region, name=district_name)
            created["districts"] += is_new

    for side, names in ORGANIZATIONS.items():
        for name in names:
            _, is_new = Organization.objects.get_or_create(side=side, name=name)
            created["organizations"] += is_new

    for position, title in enumerate(MAIN_TASK_TEMPLATE, start=1):
        _, is_new = MainTaskTemplate.objects.get_or_create(title=title, defaults={"position": position})
        created["templates"] += is_new

    return created
