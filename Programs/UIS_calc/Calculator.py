import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime

TYPES = ["Служба в УИС", "Армия", "Вуз", "Ведомственный вуз", "Отпуск по уходу за ребенком", "Правоохранительные органы"]

def days_between(start, end):
    if not start or not end:
        return 0
    try:
        d1 = datetime.strptime(start, "%d.%m.%Y")
        d2 = datetime.strptime(end, "%d.%m.%Y")
        return max(0, (d2 - d1).days)
    except:
        return 0

def days_to_str(days):
    if days <= 0:
        return "0 дней"
    years = int(days // 365.25)
    rem = days - years * 365.25
    months = int(rem // 30.44)
    rem_days = int(rem - months * 30.44)
    parts = []
    if years:
        parts.append(f"{years} лет")
    if months:
        parts.append(f"{months} мес")
    if rem_days or not parts:
        parts.append(f"{rem_days} дн")
    return " ".join(parts)

period_frames = []  # список фреймов (не используется, можно убрать, но оставим для совместимости)
periods = []        # список словарей с данными виджетов

def add_period():
    frame = tk.Frame(periods_container)
    frame.pack(fill="x", pady=2)

    type_var = tk.StringVar(value="Служба в УИС")
    combo = ttk.Combobox(frame, textvariable=type_var, values=TYPES, width=20)
    combo.pack(side="left", padx=2)

    start_entry = tk.Entry(frame, width=12)
    start_entry.pack(side="left", padx=2)
    tk.Label(frame, text="–").pack(side="left")
    end_entry = tk.Entry(frame, width=12)
    end_entry.pack(side="left", padx=2)

    coeff_label = tk.Label(frame, text="1.5", width=5)
    coeff_label.pack(side="left", padx=5)

    def update_coeff(*args):
        t = type_var.get()
        coeff_label.config(text="1.5" if t == "Служба в УИС" else "1.0")
    type_var.trace("w", update_coeff)

    def remove_period():
        # Удаляем фрейм из интерфейса
        frame.destroy()
        # Удаляем соответствующий словарь из списка periods
        for i, p in enumerate(periods):
            if p["frame"] is frame:
                periods.pop(i)
                break

    btn_del = tk.Button(frame, text="✕", command=remove_period, fg="red")
    btn_del.pack(side="left", padx=5)

    # Сохраняем данные
    periods.append({
        "frame": frame,
        "type_var": type_var,
        "start": start_entry,
        "end": end_entry,
        "coeff_label": coeff_label,
    })

def calculate():
    periods_data = []
    for p in periods:
        start = p["start"].get().strip()
        end = p["end"].get().strip()
        if not start or not end:
            continue
        period_type = p["type_var"].get()
        coeff = 1.5 if period_type == "Служба в УИС" else 1.0
        days = days_between(start, end)
        if days <= 0:
            continue
        periods_data.append({
            "type": period_type,
            "days": days,
            "coeff": coeff
        })

    if not periods_data:
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, "Нет введённых периодов.")
        return

    output = []
    output.append("=== Календарная выслуга ===\n")
    total_cal = 0
    for p in periods_data:
        duration_str = days_to_str(p["days"])
        output.append(f"{p['type']}: {duration_str}")
        total_cal += p["days"]
    output.append(f"\nВсего календарная: {days_to_str(total_cal)}\n")

    output.append("\n=== Льготная выслуга ===\n")
    total_pref = 0
    for p in periods_data:
        pref_days = round(p["days"] * p["coeff"])
        duration_str = days_to_str(pref_days)
        output.append(f"{p['type']} (коэф. {p['coeff']}): {duration_str}")
        total_pref += pref_days
    output.append(f"\nВсего льготная: {days_to_str(total_pref)}")

    result_text.delete(1.0, tk.END)
    result_text.insert(tk.END, "\n".join(output))

# Основное окно
root = tk.Tk()
root.title("Калькулятор выслуги лет (УИС)")

# Пояснение для пользователя
instruction = tk.Label(root, text="Вводите даты в формате ДД.ММ.ГГГГ (например, 01.01.2000)", 
                       font=("Arial", 10), fg="blue")
instruction.pack(pady=5)

periods_container = tk.Frame(root)
periods_container.pack(fill="both", expand=True, padx=10, pady=5)

btn_add = tk.Button(root, text="➕ Добавить период", command=add_period)
btn_add.pack(pady=5)

btn_calc = tk.Button(root, text="Рассчитать", command=calculate, bg="lightblue")
btn_calc.pack(pady=5)

result_text = scrolledtext.ScrolledText(root, height=15, width=80)
result_text.pack(padx=10, pady=10)

# Добавляем начальный период
add_period()

root.mainloop()