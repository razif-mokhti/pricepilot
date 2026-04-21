import json
from typing import Dict, Any

import pandas as pd
import streamlit as st

APP_NAME = "PricePilot"
APP_VERSION = "v0.8.4.1"
ACCESS_CODE = "pilot123"

MENU_COLUMNS = [
    "ItemID",
    "Name",
    "Category",
    "Mode",
    "Food Cost",
    "Packaging",
    "Monthly Units",
    "Current Price",
    "Target Margin",
    "Wastage",
]

CATEGORY_OPTIONS = [
    "Main dish",
    "Side dish",
    "Drink",
    "Dessert",
    "Snack",
    "Combo / Package",
    "Add-on",
    "Other",
]
MODE_OPTIONS = ["cost_only", "recipe"]

CATEGORY_GUIDELINES = {
    "Main dish": {"margin_min": 20, "margin_max": 35, "wastage_min": 5, "wastage_max": 10},
    "Side dish": {"margin_min": 20, "margin_max": 35, "wastage_min": 4, "wastage_max": 8},
    "Drink": {"margin_min": 50, "margin_max": 70, "wastage_min": 2, "wastage_max": 5},
    "Dessert": {"margin_min": 30, "margin_max": 50, "wastage_min": 5, "wastage_max": 12},
    "Snack": {"margin_min": 25, "margin_max": 40, "wastage_min": 5, "wastage_max": 10},
    "Combo / Package": {"margin_min": 20, "margin_max": 35, "wastage_min": 4, "wastage_max": 8},
    "Add-on": {"margin_min": 35, "margin_max": 60, "wastage_min": 2, "wastage_max": 6},
    "Other": {"margin_min": 20, "margin_max": 35, "wastage_min": 5, "wastage_max": 10},
}

CATEGORY_WEIGHTS = {
    "Drink": 0.30,
    "Snack": 0.50,
    "Dessert": 0.70,
    "Add-on": 0.60,
    "Other": 0.80,
    "Side dish": 0.80,
    "Main dish": 1.00,
    "Combo / Package": 1.30,
}

st.set_page_config(page_title=f"{APP_NAME} {APP_VERSION}", page_icon="📊", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 2rem;}
.hero-box {
    background: linear-gradient(135deg, #f8fbff 0%, #f3f7ff 100%);
    border: 1px solid #d9e6ff;
    border-radius: 18px;
    padding: 1.1rem 1.25rem;
    margin-bottom: 1rem;
}
.hero-badge {
    display: inline-block;
    padding: 0.32rem 0.7rem;
    border-radius: 999px;
    background: white;
    border: 1px solid #d9e6ff;
    color: #1d4ed8;
    font-size: 0.84rem;
    font-weight: 700;
    margin-bottom: 0.7rem;
}
.main-title {
    font-size: 2.55rem;
    font-weight: 800;
    color: #1f2937;
    margin-bottom: 0.1rem;
}
.sub-title {
    color: #6b7280;
    font-size: 1rem;
}
.section-title {
    font-size: 1.35rem;
    font-weight: 750;
    margin: 0.2rem 0 0.7rem 0;
}
.card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    padding: 1rem;
    box-shadow: 0 4px 14px rgba(0,0,0,0.03);
    margin-bottom: 1rem;
}
.metric-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    padding: 1rem 1rem 0.9rem 1rem;
    box-shadow: 0 4px 14px rgba(0,0,0,0.03);
    min-height: 118px;
}
.metric-label {
    color: #6b7280;
    font-size: 0.9rem;
}
.metric-value {
    color: #111827;
    font-size: 2rem;
    font-weight: 800;
    margin-top: 0.2rem;
}
.footer-box {
    background: #fafaf9;
    border: 1px dashed #d9e6ff;
    border-radius: 16px;
    padding: 0.9rem 1rem;
    margin-top: 1rem;
    color: #6b7280;
}
</style>
""", unsafe_allow_html=True)


def init_state() -> None:
    defaults = {
        "authenticated": False,
        "business_name": "Republic of Ayam Gepuk",
        "target_margin_pct": 25,
        "wastage_pct": 5,
        "tax_enabled": False,
        "tax_rate_pct": 6.0,
        "allocation_mode": "weighted",
        "last_import_signature": None,
        "next_item_id": 1,
        "pending_import": None,
        "import_message": "",
        "monthly_costs": {
            "staff_salary": 3000.0,
            "owner_salary": 5000.0,
            "rent": 2000.0,
            "utilities": 150.0,
            "internet": 200.0,
            "maintenance": 500.0,
            "misc": 150.0,
        },
        "ingredients": pd.DataFrame(
            columns=["Ingredient", "Purchase Qty", "Unit", "Purchase Cost", "Cost Per Base Unit"]
        ),
        "menu_df": pd.DataFrame(columns=MENU_COLUMNS),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def round_money(x: float) -> float:
    return round(float(x), 2)


def ensure_item_ids(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "ItemID" not in df.columns:
        df["ItemID"] = None

    existing_ids = pd.to_numeric(df["ItemID"], errors="coerce")
    max_existing = int(existing_ids.max()) if existing_ids.notna().any() else 0
    next_id = max(st.session_state.next_item_id, max_existing + 1)

    for idx in df.index:
        val = pd.to_numeric(pd.Series([df.at[idx, "ItemID"]]), errors="coerce").iloc[0]
        if pd.isna(val):
            df.at[idx, "ItemID"] = next_id
            next_id += 1
        else:
            df.at[idx, "ItemID"] = int(val)

    st.session_state.next_item_id = next_id
    return df


def apply_import_payload(payload: Dict[str, Any]) -> None:
    st.session_state.business_name = payload.get("business_name", st.session_state.business_name)
    st.session_state.target_margin_pct = int(payload.get("target_margin_pct", st.session_state.target_margin_pct))
    st.session_state.wastage_pct = int(payload.get("wastage_pct", st.session_state.wastage_pct))
    st.session_state.tax_enabled = bool(payload.get("tax_enabled", st.session_state.tax_enabled))
    st.session_state.tax_rate_pct = float(payload.get("tax_rate_pct", st.session_state.tax_rate_pct))
    st.session_state.allocation_mode = payload.get("allocation_mode", st.session_state.allocation_mode)
    st.session_state.next_item_id = int(payload.get("next_item_id", st.session_state.next_item_id))
    st.session_state.monthly_costs = payload.get("monthly_costs", st.session_state.monthly_costs)
    st.session_state.ingredients = pd.DataFrame(payload.get("ingredients", []))

    imported_menu = pd.DataFrame(payload.get("menu_df", []))
    if imported_menu.empty:
        st.session_state.menu_df = pd.DataFrame(columns=MENU_COLUMNS)
    else:
        for col in MENU_COLUMNS:
            if col not in imported_menu.columns:
                imported_menu[col] = 0 if col in [
                    "ItemID", "Food Cost", "Packaging", "Monthly Units",
                    "Current Price", "Target Margin", "Wastage"
                ] else ""
        imported_menu = ensure_item_ids(imported_menu[MENU_COLUMNS])
        st.session_state.menu_df = imported_menu


def export_payload() -> Dict[str, Any]:
    df = ensure_item_ids(st.session_state.menu_df)
    st.session_state.menu_df = df
    return {
        "business_name": st.session_state.business_name,
        "target_margin_pct": st.session_state.target_margin_pct,
        "wastage_pct": st.session_state.wastage_pct,
        "tax_enabled": st.session_state.tax_enabled,
        "tax_rate_pct": st.session_state.tax_rate_pct,
        "allocation_mode": st.session_state.allocation_mode,
        "next_item_id": st.session_state.next_item_id,
        "monthly_costs": st.session_state.monthly_costs,
        "ingredients": st.session_state.ingredients.to_dict(orient="records"),
        "menu_df": df.to_dict(orient="records"),
    }


def total_monthly_fixed_cost() -> float:
    return float(sum(float(v) for v in st.session_state.monthly_costs.values()))


def total_expected_monthly_units() -> int:
    df = st.session_state.menu_df
    if df.empty:
        return 1
    return max(int(pd.to_numeric(df["Monthly Units"], errors="coerce").fillna(0).sum()), 1)


def total_weighted_units() -> float:
    df = st.session_state.menu_df
    if df.empty:
        return 1.0
    cats = df["Category"].astype(str)
    weights = cats.map(lambda c: CATEGORY_WEIGHTS.get(c, CATEGORY_WEIGHTS["Other"]))
    units = pd.to_numeric(df["Monthly Units"], errors="coerce").fillna(0)
    total = float((units * weights).sum())
    return max(total, 1.0)


def allocation_mode_label() -> str:
    return "Category-weighted allocation" if st.session_state.allocation_mode == "weighted" else "Equal per-unit allocation"


def allocated_fixed_cost_per_unit_for_row(row: pd.Series) -> float:
    units = max(float(row.get("Monthly Units", 0) or 0), 0.0)
    if units <= 0:
        return 0.0

    total_fixed = total_monthly_fixed_cost()

    if st.session_state.allocation_mode == "equal":
        return total_fixed / total_expected_monthly_units()

    weight = CATEGORY_WEIGHTS.get(str(row.get("Category", "Other")), CATEGORY_WEIGHTS["Other"])
    weighted_pool = total_weighted_units()
    allocated_total_for_item = total_fixed * ((units * weight) / weighted_pool)
    return allocated_total_for_item / units


def effective_margin(row: pd.Series) -> float:
    row_margin = float(row.get("Target Margin", 0) or 0)
    return row_margin if row_margin > 0 else float(st.session_state.target_margin_pct)


def effective_wastage(row: pd.Series) -> float:
    row_wastage = float(row.get("Wastage", 0) or 0)
    return row_wastage if row_wastage > 0 else float(st.session_state.wastage_pct)


def recommended_price(total_cost: float, margin_pct: float) -> float:
    margin = margin_pct / 100.0
    if margin >= 1.0:
        return total_cost
    return total_cost / (1 - margin)


def benchmark_table() -> pd.DataFrame:
    rows = []
    for cat, vals in CATEGORY_GUIDELINES.items():
        rows.append({
            "Category": cat,
            "Typical Margin [%]": f"{vals['margin_min']}–{vals['margin_max']}",
            "Typical Wastage [%]": f"{vals['wastage_min']}–{vals['wastage_max']}",
            "Fixed Cost Weight [-]": CATEGORY_WEIGHTS.get(cat, 1.0),
        })
    return pd.DataFrame(rows)


def item_insight(row: pd.Series) -> str:
    if row["Status"] == "Loss-making":
        return (
            f"{row['Name']} is selling below cost. Break-even is RM {row['Break-even Price [RM]']:.2f}, "
            f"so it loses RM {abs(row['Profit/Unit [RM]']):.2f} per unit."
        )
    if row["Status"] == "Below target":
        gap = row["Recommended Price [RM]"] - row["Current Price [RM]"]
        return (
            f"{row['Name']} is profitable but still below target. Increase by about RM {gap:.2f} "
            f"to reach the target margin."
        )
    return (
        f"{row['Name']} is healthy. It meets or exceeds the target margin and earns "
        f"RM {row['Profit/Unit [RM]']:.2f} per unit."
    )


def build_dashboard_df() -> pd.DataFrame:
    df = st.session_state.menu_df.copy()
    if df.empty:
        return df

    rows = []
    for _, row in df.iterrows():
        margin = effective_margin(row)
        wastage = effective_wastage(row)
        alloc_fixed = allocated_fixed_cost_per_unit_for_row(row)
        wastage_rm = float(row["Food Cost"]) * wastage / 100.0
        total_cost = float(row["Food Cost"]) + float(row["Packaging"]) + alloc_fixed + wastage_rm
        rec_price = recommended_price(total_cost, margin)
        profit_per_unit = float(row["Current Price"]) - total_cost
        monthly_profit = profit_per_unit * int(row["Monthly Units"])
        break_even = total_cost

        if float(row["Current Price"]) < break_even:
            status = "Loss-making"
        elif float(row["Current Price"]) < rec_price:
            status = "Below target"
        else:
            status = "Healthy"

        rows.append({
            "ItemID": int(row["ItemID"]),
            "Name": row["Name"],
            "Category": row["Category"],
            "Food Cost [RM]": float(row["Food Cost"]),
            "Packaging [RM]": float(row["Packaging"]),
            "Monthly Units [unit/mo]": int(row["Monthly Units"]),
            "Current Price [RM]": float(row["Current Price"]),
            "Target Margin [%]": margin,
            "Wastage [%]": wastage,
            "Weight [-]": CATEGORY_WEIGHTS.get(str(row["Category"]), CATEGORY_WEIGHTS["Other"]),
            "Allocated Fixed Cost [RM/unit]": alloc_fixed,
            "Wastage Cost [RM/unit]": wastage_rm,
            "Total Cost [RM/unit]": total_cost,
            "Break-even Price [RM]": break_even,
            "Recommended Price [RM]": rec_price,
            "Profit/Unit [RM]": profit_per_unit,
            "Monthly Profit [RM]": monthly_profit,
            "Status": status,
        })

    return pd.DataFrame(rows)


def format_dashboard(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    money_cols = [
        "Food Cost [RM]",
        "Packaging [RM]",
        "Current Price [RM]",
        "Allocated Fixed Cost [RM/unit]",
        "Wastage Cost [RM/unit]",
        "Total Cost [RM/unit]",
        "Break-even Price [RM]",
        "Recommended Price [RM]",
        "Profit/Unit [RM]",
        "Monthly Profit [RM]",
    ]
    pct_cols = ["Target Margin [%]", "Wastage [%]"]
    num_cols = ["Weight [-]"]

    for col in money_cols:
        if col in out.columns:
            out[col] = out[col].astype(float).round(2)
    for col in pct_cols:
        if col in out.columns:
            out[col] = out[col].astype(float).round(0)
    for col in num_cols:
        if col in out.columns:
            out[col] = out[col].astype(float).round(2)

    return out


def render_metric_card(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


init_state()

# Apply pending import BEFORE any widgets are instantiated
if st.session_state.pending_import is not None:
    try:
        apply_import_payload(st.session_state.pending_import)
        st.session_state.pending_import = None
        st.session_state.import_message = "Data imported successfully."
    except Exception as exc:
        st.session_state.pending_import = None
        st.session_state.import_message = f"Could not load file: {exc}"

if not st.session_state.authenticated:
    st.title("🔒 Private Access")
    code = st.text_input("Enter access code", type="password")
    if st.button("Enter"):
        if code == ACCESS_CODE:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Wrong access code")
    st.stop()

with st.sidebar:
    st.markdown("## 📊 PricePilot")
    st.caption("Private pricing tool")
    st.info("Only people with the access code can use this app.")
    st.write("- Share the link privately")
    st.write("- Share the code privately")
    st.write("- Use cost-only mode for confidential recipes")
    if st.button("Log out"):
        st.session_state.authenticated = False
        st.rerun()

st.markdown(
    f"""
    <div class="hero-box">
        <div class="hero-badge">Private • Link-shared • Built for SMEs</div>
        <div class="main-title">📊 {APP_NAME}</div>
        <div class="sub-title">
            A practical pricing and margin tool for food businesses, hawkers, cafés, caterers, and small SMEs.
            Your data stays with you unless you export it yourself.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

tabs = st.tabs([
    "Business Setup",
    "Monthly Costs",
    "Ingredients",
    "Menu Items",
    "Pricing Dashboard",
    "Quick Check",
    "Import / Export",
])

with tabs[0]:
    st.markdown('<div class="section-title">Business Setup</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)

    c1, c2 = st.columns([1.4, 1])
    with c1:
        st.text_input("Business name [-]", key="business_name")
    with c2:
        st.checkbox("Enable tax in price display [-]", key="tax_enabled")

    c3, c4 = st.columns(2)
    with c3:
        st.slider("Default target margin [%]", 0, 90, key="target_margin_pct")
    with c4:
        st.slider("Default wastage allowance [%]", 0, 50, key="wastage_pct")

    st.number_input(
        "Tax rate [%]",
        min_value=0.0,
        max_value=20.0,
        step=1.0,
        key="tax_rate_pct",
        disabled=not st.session_state.tax_enabled,
    )

    st.radio(
        "Fixed cost allocation mode [-]",
        options=["weighted", "equal"],
        format_func=lambda x: "Category-weighted allocation" if x == "weighted" else "Equal per-unit allocation",
        key="allocation_mode",
        horizontal=True,
    )

    st.dataframe(benchmark_table(), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tabs[1]:
    st.markdown('<div class="section-title">Monthly Cost Breakdown</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)

    cols = st.columns(3)
    keys = list(st.session_state.monthly_costs.keys())
    for idx, key in enumerate(keys):
        with cols[idx % 3]:
            st.session_state.monthly_costs[key] = st.number_input(
                f"{key.replace('_', ' ').title()} [RM/mo]",
                min_value=0.0,
                value=float(st.session_state.monthly_costs[key]),
                step=50.0,
                key=f"mc_{key}",
            )

    render_metric_card("Total monthly fixed cost [RM/mo]", f"RM {total_monthly_fixed_cost():,.2f}")
    st.caption(f"Current allocation mode: {allocation_mode_label()}")
    st.markdown("</div>", unsafe_allow_html=True)

with tabs[2]:
    st.markdown('<div class="section-title">Ingredients</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.caption("Optional page. Use only if you want ingredient-level costing later.")

    with st.form("ingredient_form_v0841", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        ing_name = c1.text_input("Ingredient name [-]")
        ing_qty = c2.number_input("Purchase quantity [-]", min_value=0.0, value=1000.0, step=1.0)
        ing_unit = c3.selectbox("Unit [-]", ["g", "kg", "ml", "l", "piece", "set"])
        ing_cost = c4.number_input("Purchase cost [RM]", min_value=0.0, value=0.0, step=0.1)

        add_ing = st.form_submit_button("Add ingredient")
        if add_ing and ing_name.strip():
            factor = {"g": 1, "kg": 1000, "ml": 1, "l": 1000, "piece": 1, "set": 1}[ing_unit]
            cpu = ing_cost / (ing_qty * factor) if ing_qty > 0 else 0.0
            new_row = pd.DataFrame([{
                "Ingredient": ing_name.strip(),
                "Purchase Qty": ing_qty,
                "Unit": ing_unit,
                "Purchase Cost": round_money(ing_cost),
                "Cost Per Base Unit": round(cpu, 4),
            }])
            st.session_state.ingredients = pd.concat([st.session_state.ingredients, new_row], ignore_index=True)
            st.success(f"Added ingredient: {ing_name}")

    if st.session_state.ingredients.empty:
        st.info("No ingredients added yet.")
    else:
        st.dataframe(st.session_state.ingredients, use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)

with tabs[3]:
    st.markdown('<div class="section-title">Menu Items</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.caption("Use the form below to add a new item, or edit existing items in the table.")

    with st.form("menu_form_v0841", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Menu item name [-]")
        category = c2.selectbox("Category [-]", CATEGORY_OPTIONS)
        mode = c3.selectbox(
            "Pricing mode [-]",
            MODE_OPTIONS,
            format_func=lambda x: "Cost-only mode" if x == "cost_only" else "Recipe mode"
        )

        c4, c5, c6 = st.columns(3)
        food_cost = c4.number_input("Food cost [RM/unit]", min_value=0.0, value=0.0, step=0.1)
        packaging = c5.number_input("Packaging [RM/unit]", min_value=0.0, value=0.7, step=0.1)
        monthly_units = c6.number_input("Monthly units [unit/mo]", min_value=0, value=100, step=1)

        c7, c8, c9 = st.columns(3)
        current_price = c7.number_input("Current price [RM]", min_value=0.0, value=0.0, step=0.1)
        item_margin = c8.number_input("Target margin [%]", min_value=0.0, max_value=90.0, value=float(st.session_state.target_margin_pct), step=1.0)
        item_wastage = c9.number_input("Wastage [%]", min_value=0.0, max_value=50.0, value=float(st.session_state.wastage_pct), step=1.0)

        if st.form_submit_button("Add new menu item"):
            if not name.strip():
                st.error("Menu item name is required.")
            else:
                df = ensure_item_ids(st.session_state.menu_df)
                new_row = pd.DataFrame([{
                    "ItemID": st.session_state.next_item_id,
                    "Name": name.strip(),
                    "Category": category,
                    "Mode": mode,
                    "Food Cost": round_money(food_cost),
                    "Packaging": round_money(packaging),
                    "Monthly Units": int(monthly_units),
                    "Current Price": round_money(current_price),
                    "Target Margin": float(item_margin),
                    "Wastage": float(item_wastage),
                }])
                st.session_state.next_item_id += 1
                st.session_state.menu_df = pd.concat([df, new_row], ignore_index=True)
                st.success(f"Added menu item: {name.strip()}")
                st.rerun()

    editable_df = ensure_item_ids(st.session_state.menu_df.copy())
    st.session_state.menu_df = editable_df

    if editable_df.empty:
        st.info("No menu items yet.")
    else:
        edited_df = st.data_editor(
            editable_df,
            use_container_width=True,
            num_rows="fixed",
            hide_index=True,
            column_config={
                "ItemID": st.column_config.NumberColumn("ItemID [-]", disabled=True, format="%d"),
                "Name": st.column_config.TextColumn("Name [-]", required=True),
                "Category": st.column_config.SelectboxColumn("Category [-]", options=CATEGORY_OPTIONS),
                "Mode": st.column_config.SelectboxColumn("Mode [-]", options=MODE_OPTIONS),
                "Food Cost": st.column_config.NumberColumn("Food Cost [RM/unit]", format="%.2f"),
                "Packaging": st.column_config.NumberColumn("Packaging [RM/unit]", format="%.2f"),
                "Monthly Units": st.column_config.NumberColumn("Monthly Units [unit/mo]", format="%d"),
                "Current Price": st.column_config.NumberColumn("Current Price [RM]", format="%.2f"),
                "Target Margin": st.column_config.NumberColumn("Target Margin [%]", format="%.0f"),
                "Wastage": st.column_config.NumberColumn("Wastage [%]", format="%.0f"),
            },
            key="menu_table_editor_v0841",
        )

        if st.button("Apply table edits", key="apply_table_edits_v0841"):
            clean = edited_df.copy()
            clean["Name"] = clean["Name"].astype(str).str.strip()
            clean = clean[clean["Name"] != ""].copy()
            clean = clean.drop_duplicates(subset=["ItemID"], keep="last").reset_index(drop=True)
            for col in ["Food Cost", "Packaging", "Monthly Units", "Current Price", "Target Margin", "Wastage"]:
                clean[col] = pd.to_numeric(clean[col], errors="coerce").fillna(0)
            clean["ItemID"] = pd.to_numeric(clean["ItemID"], errors="coerce").fillna(0).astype(int)
            clean["Monthly Units"] = clean["Monthly Units"].astype(int)
            clean = ensure_item_ids(clean[MENU_COLUMNS])
            st.session_state.menu_df = clean
            st.success("Table edits applied.")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

with tabs[4]:
    st.markdown('<div class="section-title">Pricing Dashboard</div>', unsafe_allow_html=True)
    dashboard_df = build_dashboard_df()

    if dashboard_df.empty:
        st.warning("Add at least one menu item first.")
    else:
        equal_alloc = total_monthly_fixed_cost() / total_expected_monthly_units()

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_metric_card("Total monthly fixed cost [RM/mo]", f"RM {total_monthly_fixed_cost():,.2f}")
        with c2:
            render_metric_card("Total expected monthly units [unit/mo]", f"{total_expected_monthly_units():,}")
        with c3:
            render_metric_card("Equal fixed cost / unit [RM]", f"RM {equal_alloc:,.2f}")
        with c4:
            render_metric_card("Allocation mode [-]", allocation_mode_label())

        display_df = dashboard_df[[
            "ItemID",
            "Name",
            "Category",
            "Target Margin [%]",
            "Wastage [%]",
            "Weight [-]",
            "Allocated Fixed Cost [RM/unit]",
            "Total Cost [RM/unit]",
            "Break-even Price [RM]",
            "Recommended Price [RM]",
            "Current Price [RM]",
            "Profit/Unit [RM]",
            "Monthly Profit [RM]",
            "Status",
        ]].copy()

        st.dataframe(format_dashboard(display_df), use_container_width=True, hide_index=True)

        st.markdown("### Item insights")
        for _, row in format_dashboard(dashboard_df).iterrows():
            st.write(f"• **Item {int(row['ItemID'])} — {row['Name']}**: {item_insight(row)}")

        if st.session_state.allocation_mode == "weighted":
            st.info(
                f"Weighted allocation uses category weights and a weighted unit pool of {total_weighted_units():,.2f} [-]. "
                "This gives low-ticket categories like drinks and snacks a smaller fixed-cost burden."
            )
        else:
            st.info("Equal allocation gives every sold unit the same fixed-cost burden.")

with tabs[5]:
    st.markdown('<div class="section-title">Quick Check</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)

    qc_mode = st.radio(
        "Quick Check mode [-]",
        options=["Manual scenario", "Use existing item"],
        horizontal=True,
    )

    if qc_mode == "Use existing item" and not st.session_state.menu_df.empty:
        options = {f"{int(r.ItemID)} - {r.Name}": r for _, r in st.session_state.menu_df.iterrows()}
        selected_key = st.selectbox("Select item [-]", list(options.keys()))
        base_row = options[selected_key]

        q_cost = float(base_row["Food Cost"])
        q_pack = float(base_row["Packaging"])
        q_price = float(base_row["Current Price"])
        applied_margin = effective_margin(base_row)
        applied_wastage = effective_wastage(base_row)
        q_fixed = allocated_fixed_cost_per_unit_for_row(base_row)

        st.caption(f"Quick Check currently refers to: Item {int(base_row['ItemID'])} — {base_row['Name']}")
    else:
        st.selectbox("Category [-]", CATEGORY_OPTIONS, key="qc_category_v0841")
        q_cost = st.number_input("Food cost [RM/unit]", min_value=0.0, value=10.0, step=0.1)
        q_pack = st.number_input("Packaging [RM/unit]", min_value=0.0, value=0.7, step=0.1)
        q_fixed = st.number_input("Fixed cost per unit [RM/unit]", min_value=0.0, value=1.0, step=0.1)
        q_price = st.number_input("Current selling price [RM]", min_value=0.0, value=12.0, step=0.1)
        applied_margin = st.slider("Target margin [%]", 0, 90, int(st.session_state.target_margin_pct))
        applied_wastage = st.slider("Wastage [%]", 0, 50, int(st.session_state.wastage_pct))

    wastage_rm = q_cost * applied_wastage / 100.0
    total_cost = q_cost + q_pack + q_fixed + wastage_rm
    rec_price = recommended_price(total_cost, applied_margin)
    profit_unit = q_price - total_cost

    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric_card("Estimated total cost [RM/unit]", f"RM {round_money(total_cost):.2f}")
    with c2:
        render_metric_card("Recommended price [RM]", f"RM {round_money(rec_price):.2f}")
    with c3:
        render_metric_card("Current profit / unit [RM]", f"RM {round_money(profit_unit):.2f}")

    st.markdown("### Cost breakdown")
    st.write(f"Food cost [RM/unit]: **RM {q_cost:.2f}**")
    st.write(f"Wastage [{applied_wastage:.0f}%]: **+RM {wastage_rm:.2f}**")
    st.write(f"Packaging [RM/unit]: **RM {q_pack:.2f}**")
    st.write(f"Fixed cost [RM/unit]: **RM {q_fixed:.2f}**")
    st.write(f"Estimated total cost [RM/unit]: **RM {total_cost:.2f}**")

    st.markdown("### Margin scenarios")
    rows = []
    for m in [10, 15, 20, 25, 30, 35, 40]:
        rows.append({
            "Margin [%]": m,
            "Recommended Price [RM]": round_money(recommended_price(total_cost, m)),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("### Quick insight")
    if q_price < total_cost:
        st.error(f"This scenario is loss-making. Raise price or reduce cost by RM {abs(profit_unit):.2f} per unit.")
    elif q_price < rec_price:
        st.warning(f"This scenario covers cost, but it is still below the target-margin price by RM {rec_price - q_price:.2f}.")
    else:
        st.success("This scenario meets or exceeds the target margin.")

    st.markdown("</div>", unsafe_allow_html=True)

with tabs[6]:
    st.markdown('<div class="section-title">Import / Export</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)

    if st.session_state.import_message:
        if "successfully" in st.session_state.import_message.lower():
            st.success(st.session_state.import_message)
        else:
            st.error(st.session_state.import_message)

    st.caption("Download JSON exports the full current app state: business setup, monthly costs, ingredients, allocation mode, and all menu items.")

    payload = export_payload()
    st.download_button(
        label="Download full app state as JSON",
        data=json.dumps(payload, indent=2).encode("utf-8"),
        file_name="pricepilot_v08_4_1_full_state.json",
        mime="application/json",
    )

    uploaded = st.file_uploader("Upload JSON state file [-]", type=["json"], key="uploader_v0841")

    if uploaded is not None:
        import_signature = f"{uploaded.name}-{uploaded.size}"

        if st.button("Import data from uploaded JSON", key="import_btn_v0841"):
            try:
                imported = json.load(uploaded)
                st.session_state.pending_import = imported
                st.session_state.last_import_signature = import_signature
                st.session_state.import_message = ""
                st.rerun()
            except Exception as exc:
                st.session_state.import_message = f"Could not load file: {exc}"

        if st.session_state.last_import_signature == import_signature:
            st.info("This file has already been uploaded in the current session.")

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="footer-box">
        <b>{APP_NAME} {APP_VERSION}</b> • fixed import timing • full monthly cost breakdown • stable ItemID • dropdown categories • richer insights • unit labels.
    </div>
    """,
    unsafe_allow_html=True,
)