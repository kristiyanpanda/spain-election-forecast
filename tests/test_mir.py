from electoral.mir import LAYOUT_03, LAYOUT_07, LAYOUT_08, _read_fixed

# real records from 02202307_TOTA.zip (Almería, PP national head 000005)
REC_08 = "022023071010490000010000050000000"
REC_07 = ("02202307101049Almería" + " " * 43 +
          "00740534008370051610800516114000000000000000000192996002468960000246400003163003187780000060000000000000000S")


def test_layout_widths():
    assert sum(w for _, w in LAYOUT_08) == 33
    assert sum(w for _, w in LAYOUT_07) == 172
    assert sum(w for _, w in LAYOUT_03) == 232


def test_parse_08_record():
    df = _read_fixed(REC_08.encode("latin-1"), LAYOUT_08)
    r = df.iloc[0]
    assert (r.tipo, r.anio, r.mes, r.vuelta, r.ccaa, r.prov, r.distrito) == ("02", "2023", "07", "1", "01", "04", "9")
    assert r.cand_code == "000001" and r.votos == "00000500" and r.escanos == "00000"


def test_parse_07_record_totals_are_consistent():
    df = _read_fixed(REC_07.encode("latin-1"), LAYOUT_07)
    r = df.iloc[0]
    assert r.ambito_nombre == "Almería"
    blank, null, lists = int(r.votos_blancos), int(r.votos_nulos), int(r.votos_candidaturas)
    assert (blank, null, lists) == (2464, 3163, 318778)
    assert int(r.escanos) == 6 and int(r.censo_escrutinio) == 516114
