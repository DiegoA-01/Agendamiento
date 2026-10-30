from apps.tenancy.dns import DnsLookupError


class FakeResolver:
    """DNS controlado por el test: `FakeResolver.txt_records["nombre"] = ["valor"]`."""

    txt_records: dict[str, list[str]] = {}
    cname_records: dict[str, list[str]] = {}
    fail = False
    fail_cname = False

    @classmethod
    def reset(cls) -> None:
        cls.txt_records = {}
        cls.cname_records = {}
        cls.fail = False
        cls.fail_cname = False

    def txt(self, name: str) -> list[str]:
        if self.fail:
            raise DnsLookupError("sin red")
        return self.txt_records.get(name, [])

    def cname(self, name: str) -> list[str]:
        if self.fail or self.fail_cname:
            raise DnsLookupError("sin red")
        return self.cname_records.get(name, [])
