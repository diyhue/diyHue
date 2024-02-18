from flask_restful import Resource

class Credits(Resource):
    def get(self, resource):
        if resource == "packages.json":
            response = [
                {
                    "Attributions": [],
                    "SPDX-License-Identifiers": [
                        ""
                    ],
                  "SourceLinks": [
                        "https://github.com/mariusmotea",
                    ],
                    "licenses": {
                        "Main Developer & Mastermind of DiyHue":""
                    },
                    "Version": "",
                    "Package": "Marius",
                    "Website": "https://github.com/mariusmotea"
                },
                {
                    "Attributions": [],
                    "SPDX-License-Identifiers": [
                        ""
                    ],
                  "SourceLinks": [
                        "https://github.com/cheesemarathon",
                    ],
                    "licenses": {
                        "Github & CI/CD Wizard":""
                    },
                    "Version": "",
                    "Package": "cheesemarathon",
                    "Website": "https://github.com/cheesemarathon"
                },
                {
                    "Attributions": [],
                    "SPDX-License-Identifiers": [
                        ""
                    ],
                  "SourceLinks": [
                        "https://github.com/Mevel",
                    ],
                    "licenses": {
                        "Maintainer & Support":""
                    },
                    "Version": "",
                    "Package": "Mevel",
                    "Website": "https://github.com/Mevel"
                },
                {
                    "Attributions": [],
                    "SPDX-License-Identifiers": [
                        ""
                    ],
                  "SourceLinks": [
                        "https://github.com/fisico",
                    ],
                    "licenses": {
                        "Designed and developed the user interface":""
                    },
                    "Version": "",
                    "Package": "David",
                    "Website": "https://github.com/fisico"
                },
                {
                    "Attributions": [],
                    "SPDX-License-Identifiers": [
                        ""
                    ],
                  "SourceLinks": [
                        "https://github.com/philharmonie",
                    ],
                    "licenses": {
                        "React consultant":""
                    },
                    "Version": "",
                    "Package": "Phil",
                    "Website": "https://github.com/philharmonie"
                },
                {
                    "Attributions": [],
                    "SPDX-License-Identifiers": [
                        ""
                    ],
                  "SourceLinks": [
                        "https://github.com/hendriksen-mark",
                    ],
                    "licenses": {
                        "Maintainer & Support":""
                    },
                    "Version": "",
                    "Package": "Mark",
                    "Website": "https://github.com/hendriksen-mark"
                },
                {
                    "Attributions": [],
                    "SPDX-License-Identifiers": [
                        ""
                    ],
                  "SourceLinks": [
                        "https://github.com/diyhue/diyHue/graphs/contributors",
                    ],
                    "licenses": {
                        "A big thank you to everyone contributing to this project":""
                    },
                    "Version": "",
                    "Package": "Thank you!",
                    "Website": "https://github.com/diyhue/diyHue/graphs/contributors"
                }
            ]
            return response
        elif resource == "hardcoded.json":
            response = [
                {
                    "Attributions": [],
                    "SPDX-License-Identifiers": [
                        ""
                    ],
                  "SourceLinks": [
                        "https://github.com/diyhue/diyHue",
                    ],
                    "licenses": {
                        "Main diyHue software repo":""
                    },
                    "Version": "",
                    "Package": "DiyHue",
                    "Website": "https://github.com/diyhue/diyHue"
                }
            ]
            return response
        elif resource == "rust-packages.json":
            response = [
                {
                    "Attributions": [],
                    "SPDX-License-Identifiers": [
                        ""
                    ],
                  "SourceLinks": [
                        "https://github.com/diyhue",
                    ],
                    "licenses": {
                        "diyHue repositories":""
                    },
                    "Version": "",
                    "Package": "DiyHue Repositories",
                    "Website": "https://github.com/diyhue"
                }
            ]
            return response