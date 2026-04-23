def compare_fingerprints(current, new):
    current_data = {(data["ident"], data["size"], data["date"]) for data in current}
    new_data = {(data["ident"], data["size"], data["date"]) for data in new}
    return new_data - current_data


def filter_datas(datas_current, datas_old):
    datas = []
    old_data_tuples = {(data["ident"], data["size"], data["date"]) for data in datas_old}

    for data in datas_current:
        data_tuple = (data["ident"], data["size"], data["date"])
        if data_tuple not in old_data_tuples:
            datas.append(data)

    return datas
