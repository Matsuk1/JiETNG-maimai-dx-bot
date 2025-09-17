def get_note_score(notes):
    tap_num = notes['tap']
    hold_num = notes['hold']
    slide_num = notes['slide']
    touch_num = notes['touch']
    break_num = notes['break']

    tap_base = [500, 400, 250]
    hold_base = [1000, 800, 500]
    slide_base = [1500, 1200, 750]
    touch_base = tap_base
    break_base = [2500, 2500, 2500, 2000, 1500, 1250, 1000]
    break_add = [100, 75, 50, 40, 40, 40, 30]

    tap_base_total = tap_num * 500
    hold_base_total = hold_num * 1000
    slide_base_total = slide_num * 1500
    touch_base_total = touch_num * 500
    break_base_total = break_num * 2500
    break_add_total = break_num * 100

    total_base = tap_base_total + hold_base_total + slide_base_total + touch_base_total + break_base_total

    note_score = {
        'tap_great': round((tap_base[0] - tap_base[1]) / total_base * 100, 5),
        'tap_good': round((tap_base[0] - tap_base[2]) / total_base * 100, 5),
        'tap_miss': round(tap_base[0] / total_base * 100, 5),

        'hold_great': round((hold_base[0] - hold_base[1]) / total_base * 100, 5),
        'hold_good': round((hold_base[0] - hold_base[2]) / total_base * 100, 5),
        'hold_miss': round(hold_base[0] / total_base * 100, 5),

        'slide_great': round((slide_base[0] - slide_base[1]) / total_base * 100, 5),
        'slide_good': round((slide_base[0] - slide_base[2]) / total_base * 100, 5),
        'slide_miss': round(slide_base[0] / total_base * 100, 5),

        'touch_great': round((touch_base[0] - touch_base[1]) / total_base * 100, 5),
        'touch_good': round((touch_base[0] - touch_base[2]) / total_base * 100, 5),
        'touch_miss': round(touch_base[0] / total_base * 100, 5),

        'break_high_perfect': round(((break_base[0] - break_base[1]) / total_base * 100) + ((break_add[0] - break_add[1]) / break_add_total), 5),
        'break_low_perfect': round(((break_base[0] - break_base[2]) / total_base * 100) + ((break_add[0] - break_add[2]) / break_add_total), 5),
        'break_high_great': round(((break_base[0] - break_base[3]) / total_base * 100) + ((break_add[0] - break_add[3]) / break_add_total), 5),
        'break_middle_great': round(((break_base[0] - break_base[4]) / total_base * 100) + ((break_add[0] - break_add[4]) / break_add_total), 5),
        'break_low_great': round(((break_base[0] - break_base[5]) / total_base * 100) + ((break_add[0] - break_add[5]) / break_add_total), 5),
        'break_good': round(((break_base[0] - break_base[6]) / total_base * 100) + ((break_add[0] - break_add[6]) / break_add_total), 5),
        'break_miss': round((break_base[0] / total_base * 100) + (break_add[0] / break_add_total), 5)
    }

    return note_score

def calc_score(notes, judgements):
    scores = get_note_score(notes)
    total_deduction = 0
    for k, v in judgements.items():
        if k in scores:
            total_deduction += scores[k] * v
    return round(101 - total_deduction, 4)

