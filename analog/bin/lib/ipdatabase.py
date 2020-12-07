from ipdb import City


class ipDatabase(City):

    def __init__(self, db_path):
        super().__init__(db_path)

    def find(self, ip, language="CN"):
        return super().find(ip, language)
