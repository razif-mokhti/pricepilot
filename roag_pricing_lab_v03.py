"""
ROAG Pricing Lab
Version: v0.3

What's new in v0.3
- Personalized UI / branding
- Privacy-first local-only workflow
- Cost-only mode for confidential recipes
- Profit / loss alert
- Recommendation engine
- Quick price check page
- Pricing dashboard with clearer business insight

Run:
    pip install streamlit pandas
    py -m streamlit run roag_pricing_lab_v03.py
"""

import json
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any

import pandas as pd
import streamlit as st


# -------------------------------------------------
# Page config
# -------------------------------------------------
st.set_page_config(
    page_title="ROAG Pricing Lab v0.3",
    page_icon="🍗",
    layout="wide",
)

# -------------------------------------------------
# Custom styling
# -------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --brand: #d97706;
        --brand-dark: #9a3412;
        --brand-soft: #fff7ed;
        --card-border: #f3e8d7;
        --ok-bg: #dcfce7;
        --ok: #166534;
        --warn-bg: #ffedd5;
        --warn: #9a3412;
        --danger-bg: #fee2e2;
        --danger: #991b1b;
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }

    [data-testid="stSidebar"] {
        background: #fcfcfb;
    }

    .hero-box {
        background: linear-gradient(135deg, #fff7ed 0%, #fffbeb 100%);
        border: 1px solid #fde7c7;
        border-radius: 20px;
        padding: 1.2rem 1.35rem;
        margin-bottom: 1rem;
    }

    .hero-badge {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        background: white;
        border: 1px solid #f5d6a4;
        color: var(--brand-dark);
        font-size: 0.86rem;
        font-weight: 700;
        margin-bottom: 0.8rem;
    }

    .main-title {
        font-size: 2.65rem;
        font-weight: 800;
        color: #2f2f3a;
        margin-bottom: 0.15rem;
    }

    .sub-title {
        color: #6b7280;
        font-size: 1rem;
    }

    .section-title {
        font-size: 1.4rem;
        font-weight: 750;
        margin: 0.15rem 0 0.8rem 0;
    }

    .card {
        background: white;
        border: 1px solid var(--card-border);
        border-radius: 18px;
        padding: 1rem;
        box-shadow: 0 4px 14px rgba(0,0,0,0.03);
        margin-bottom: 1rem;
    }

    .metric-card {
        background: white;
        border: 1px solid var(--card-border);
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
        color: #262b33;
        font-size: 2rem;
        font-weight: 800;
        margin-top: 0.2rem;
    }

    .pill {
        display: inline-block;
        padding: 0.28rem 0.7rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
    }

    .pill-ok {
        background: var(--ok-bg);
        color: var(--ok);
    }

    .pill-warn {
        background: var(--warn-bg);
        color: var(--warn);
    }

    .pill-danger {
        background: var(--danger-bg);
        color: var(--danger);
    }

    .footer-box {
        background: #fafaf9;
        border: 1px dashed #e7d6bf;
        border-radius: 16px;
        padding: 0.9rem 1rem;
        margin-top: 1rem;
        color: #6b7280;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Data models
# -------------------------------------------------
@dataclass
class Ingredient:
    name: str
    purchase_quantity: float
    purchase_unit: str
    purchase_cost: float
    cost_per_unit: float


@dataclass
class RecipeItem:
    ingredient_name: str
    quantity_used: float
    unit_used: str
    cost_per_dish: float


@dataclass
class MenuItem:
    name: str
    category: str
    pricing_mode: str  # recipe / cost_only
    direct_food_cost: float
    packaging_cost: float
    expected_monthly_units: int
    current_selling_price: float
    recipe_items: List[Dict[str, Any]] = field(default_factory=list)


# -------------------------------------------------
# Session state
# -------------------------------------------------
def init_state() -> None:
    defaults = {
        "business_name": "Republic of Ayam Gepuk",
        "target_margin_pct": 30.0,
        "tax_enabled": False,
        "tax_rate_pct": 6.0,
        "wastage_pct": 5.0,
        "monthly_costs": {
            "staff_salary": 0.0,
            "owner_salary": 0.0,
            "rent": 0.0,
            "utilities": 0.0,
            "internet": 0.0,
            "maintenance": 0.0,
            "misc": 0.0,
        },
        "ingredients": [],
        "menu_items": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()

# -------------------------------------------------
# Helpers
# -------------------------------------------------
UNIT_MAP = {
    "g": 1.0,
    "kg": 1000.0,
    "ml": 1.0,
    "l": 1000.0,
    "piece": 1.0,
    "set": 1.0,
}


def normalize_to_base(quantity: float, unit: str) -> float:
    return quantity * UNIT_MAP.get(unit, 1.0)


def compute_cost_per_unit(purchase_quantity: float, purchase_unit: str, purchase_cost: float) -> float:
    base_qty = normalize_to_base(purchase_quantity, purchase_unit)
    if base_qty <= 0:
        return 0.0
    return purchase_cost / base_qty


def total_monthly_fixed_cost() -> float:
    return sum(float(v) for v in st.session_state["monthly_costs"].values())


def total_expected_monthly_units() -> int:
    units = sum(int(item["expected_monthly_units"]) for item in st.session_state["menu_items"])
    return max(units, 1)


def allocated_fixed_cost_per_unit() -> float:
    return total_monthly_fixed_cost() / total_expected_monthly_units()


def apply_wastage(food_cost: float) -> float:
    return food_cost * (1 + st.session_state["wastage_pct"] / 100.0)


def recommended_price(total_cost: float, margin_pct: float) -> float:
    margin = margin_pct / 100.0
    if margin >= 1.0:
        return total_cost
    return total_cost / (1 - margin)


def price_incl_tax(price_excl_tax: float) -> float:
    if not st.session_state["tax_enabled"]:
        return price_excl_tax
    return price_excl_tax * (1 + st.session_state["tax_rate_pct"] / 100.0)


def export_payload() -> Dict[str, Any]:
    return {
        "business_name": st.session_state["business_name"],
        "target_margin_pct": st.session_state["target_margin_pct"],
        "tax_enabled": st.session_state["tax_enabled"],
        "tax_rate_pct": st.session_state["tax_rate_pct"],
        "wastage_pct": st.session_state["wastage_pct"],
        "monthly_costs": st.session_state["monthly_costs"],
        "ingredients": st.session_state["ingredients"],
        "menu_items": st.session_state["menu_items"],
    }


def import_payload(payload: Dict[str, Any]) -> None:
    allowed_keys = {
        "business_name",
        "target_margin_pct",
        "tax_enabled",
        "tax_rate_pct",
        "wastage_pct",
        "monthly_costs",
        "ingredients",
        "menu_items",
    }
    for key in allowed_keys:
        if key in payload:
            st.session_state[key] = payload[key]


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


def health_label(price_gap: float) -> str:
    if price_gap <= 0.5:
        return "Healthy"
    if price_gap <= 3.0:
        return "Slightly underpriced"
    return "Underpriced"


def recommendation_text(price_gap: float, rec_price: float, margin: float) -> str:
    if price_gap <= 0.5:
        return "Current price is already close to your target pricing level."
    if price_gap <= 3.0:
        return (
            f"Consider a small price increase toward RM {rec_price:.2f} "
            f"to reach the target margin of {margin:.0f}%."
        )
    return (
        f"Increase the selling price to around RM {rec_price:.2f} "
        f"to reach the target margin of {margin:.0f}%."
    )


# -------------------------------------------------
# Sidebar
# -------------------------------------------------
with st.sidebar:
    st.markdown("## 🍗 ROAG Pricing Lab")
    st.caption("Privacy-first F&B pricing tool")
    st.info(
        "Local-first usage. No login, no cloud sync, no admin access, and no forced recipe disclosure."
    )
    st.write("- Run locally on own laptop")
    st.write("- Keep recipes private with cost-only mode")
    st.write("- Export data only to own file")

    st.divider()
    page = st.radio(
        "Navigation",
        [
            "Business Setup",
            "Monthly Costs",
            "Ingredients",
            "Menu Items",
            "Pricing Dashboard",
            "Quick Check",
            "Import / Export",
        ],
        label_visibility="collapsed",
    )

# -------------------------------------------------
# Header
# -------------------------------------------------
st.markdown(
    """
    <div class="hero-box">
        <div class="hero-badge">Privacy-first • Local-first • Built for Malaysian F&B</div>
        <div class="main-title">🍗 ROAG Pricing Lab</div>
        <div class="sub-title">
            A practical pricing and margin tool for small food businesses, hawkers, cafés, and caterers.
            Your data stays with you unless you export it yourself.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Business Setup
# -------------------------------------------------
if page == "Business Setup":
    st.markdown('<div class="section-title">Business setup</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.session_state["business_name"] = st.text_input(
            "Business name", value=st.session_state["business_name"]
        )
    with c2:
        st.session_state["target_margin_pct"] = st.number_input(
            "Default target margin (%)",
            min_value=0.0,
            max_value=90.0,
            value=float(st.session_state["target_margin_pct"]),
            step=1.0,
        )
    with c3:
        st.session_state["wastage_pct"] = st.number_input(
            "Wastage allowance (%)",
            min_value=0.0,
            max_value=50.0,
            value=float(st.session_state["wastage_pct"]),
            step=1.0,
        )

    c4, c5 = st.columns(2)
    with c4:
        st.session_state["tax_enabled"] = st.checkbox(
            "Enable tax in price display",
            value=bool(st.session_state["tax_enabled"]),
        )
    with c5:
        st.session_state["tax_rate_pct"] = st.number_input(
            "Tax rate (%)",
            min_value=0.0,
            max_value=20.0,
            value=float(st.session_state["tax_rate_pct"]),
            step=1.0,
            disabled=not st.session_state["tax_enabled"],
        )

    st.success("Settings remain local in the current browser session unless you export them.")
    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------
# Monthly Costs
# -------------------------------------------------
elif page == "Monthly Costs":
    st.markdown('<div class="section-title">Monthly cost allocation</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.caption(
        "Include staff salary and owner salary so the recommended price reflects real business sustainability."
    )

    cols = st.columns(3)
    keys = list(st.session_state["monthly_costs"].keys())

    for idx, key in enumerate(keys):
        with cols[idx % 3]:
            st.session_state["monthly_costs"][key] = st.number_input(
                key.replace("_", " ").title(),
                min_value=0.0,
                value=float(st.session_state["monthly_costs"][key]),
                step=50.0,
                key=f"mc_{key}",
            )

    st.metric("Total monthly fixed cost", f"RM {total_monthly_fixed_cost():,.2f}")
    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------
# Ingredients
# -------------------------------------------------
elif page == "Ingredients":
    st.markdown('<div class="section-title">Ingredient master</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.caption("Use this only if the owner is comfortable entering ingredient-level costing.")

    with st.form("ingredient_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        name = c1.text_input("Ingredient name")
        purchase_quantity = c2.number_input("Purchase quantity", min_value=0.0, value=1000.0, step=1.0)
        purchase_unit = c3.selectbox("Purchase unit", ["g", "kg", "ml", "l", "piece", "set"])
        purchase_cost = c4.number_input("Purchase cost (RM)", min_value=0.0, value=0.0, step=0.1)

        submitted = st.form_submit_button("Add ingredient")
        if submitted and name.strip():
            cpu = compute_cost_per_unit(purchase_quantity, purchase_unit, purchase_cost)
            ing = Ingredient(
                name=name.strip(),
                purchase_quantity=purchase_quantity,
                purchase_unit=purchase_unit,
                purchase_cost=purchase_cost,
                cost_per_unit=cpu,
            )
            st.session_state["ingredients"].append(asdict(ing))
            st.success(f"Added ingredient: {name}")

    if st.session_state["ingredients"]:
        df = pd.DataFrame(st.session_state["ingredients"])
        df["cost_per_unit"] = df["cost_per_unit"].map(lambda x: round(float(x), 4))
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No ingredients added yet.")

    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------
# Menu Items
# -------------------------------------------------
elif page == "Menu Items":
    st.markdown('<div class="section-title">Menu items</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.caption("Choose recipe mode or privacy-friendly cost-only mode.")

    pricing_mode = st.radio(
        "Pricing mode",
        ["recipe", "cost_only"],
        format_func=lambda x: "Recipe mode" if x == "recipe" else "Cost-only mode (privacy-friendly)",
        horizontal=True,
    )

    with st.form("menu_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        menu_name = c1.text_input("Menu item name")
        category = c2.text_input("Category", value="Main dish")
        packaging_cost = c3.number_input("Packaging cost (RM)", min_value=0.0, value=0.70, step=0.1)
        expected_units = c4.number_input("Expected monthly units", min_value=1, value=100, step=1)

        c5, c6 = st.columns(2)
        current_price = c5.number_input("Current selling price (RM)", min_value=0.0, value=0.0, step=0.1)

        recipe_items = []
        direct_food_cost = 0.0

        if pricing_mode == "cost_only":
            direct_food_cost = c6.number_input(
                "Direct food cost per dish (RM)",
                min_value=0.0,
                value=0.0,
                step=0.1,
                help="Use this if the recipe is confidential. No ingredient breakdown required.",
            )
            st.info("Cost-only mode protects recipe secrecy while still allowing proper pricing.")
        else:
            if not st.session_state["ingredients"]:
                st.warning("Add ingredients first, or switch to cost-only mode.")
            else:
                st.write("### Recipe builder")
                ingredient_options = [i["name"] for i in st.session_state["ingredients"]]
                row_count = st.number_input("Number of recipe lines", min_value=1, max_value=10, value=3, step=1)
                ingredient_lookup = {i["name"]: i for i in st.session_state["ingredients"]}

                for i in range(int(row_count)):
                    r1, r2, r3 = st.columns([2, 1, 1])
                    ing_name = r1.selectbox(f"Ingredient {i+1}", ingredient_options, key=f"ing_{i}")
                    qty_used = r2.number_input(
                        f"Qty used {i+1}", min_value=0.0, value=0.0, step=1.0, key=f"qty_{i}"
                    )
                    unit_used = r3.selectbox(
                        f"Unit {i+1}", ["g", "kg", "ml", "l", "piece", "set"], key=f"unit_{i}"
                    )

                    if qty_used > 0:
                        base_qty = normalize_to_base(qty_used, unit_used)
                        item_cost = base_qty * float(ingredient_lookup[ing_name]["cost_per_unit"])
                        recipe_items.append(
                            asdict(
                                RecipeItem(
                                    ingredient_name=ing_name,
                                    quantity_used=qty_used,
                                    unit_used=unit_used,
                                    cost_per_dish=item_cost,
                                )
                            )
                        )
                        direct_food_cost += item_cost

        submit_menu = st.form_submit_button("Save menu item")

        if submit_menu and menu_name.strip():
            item = MenuItem(
                name=menu_name.strip(),
                category=category.strip() or "Uncategorized",
                pricing_mode=pricing_mode,
                direct_food_cost=round(direct_food_cost, 2),
                packaging_cost=float(packaging_cost),
                expected_monthly_units=int(expected_units),
                current_selling_price=float(current_price),
                recipe_items=recipe_items,
            )
            st.session_state["menu_items"].append(asdict(item))
            st.success(f"Saved menu item: {menu_name}")

    if st.session_state["menu_items"]:
        rows = []
        for item in st.session_state["menu_items"]:
            rows.append(
                {
                    "Name": item["name"],
                    "Category": item["category"],
                    "Mode": item["pricing_mode"],
                    "Food Cost": item["direct_food_cost"],
                    "Packaging": item["packaging_cost"],
                    "Monthly Units": item["expected_monthly_units"],
                    "Current Price": item["current_selling_price"],
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No menu items yet.")

    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------
# Pricing Dashboard
# -------------------------------------------------
elif page == "Pricing Dashboard":
    st.markdown('<div class="section-title">Pricing dashboard</div>', unsafe_allow_html=True)

    if not st.session_state["menu_items"]:
        st.warning("Add at least one menu item first.")
    else:
        alloc_fixed = allocated_fixed_cost_per_unit()

        m1, m2, m3 = st.columns(3)
        with m1:
            render_metric_card("Total monthly fixed cost", f"RM {total_monthly_fixed_cost():,.2f}")
        with m2:
            render_metric_card("Total expected monthly units", f"{total_expected_monthly_units():,}")
        with m3:
            render_metric_card("Allocated fixed cost / unit", f"RM {alloc_fixed:,.2f}")

        summary_rows = []
        for item in st.session_state["menu_items"]:
            adjusted_food_cost = apply_wastage(float(item["direct_food_cost"]))
            total_cost = adjusted_food_cost + float(item["packaging_cost"]) + alloc_fixed
            rec_price = recommended_price(total_cost, st.session_state["target_margin_pct"])
            gap = rec_price - float(item["current_selling_price"])
            current_profit_per_unit = float(item["current_selling_price"]) - total_cost
            monthly_profit_at_current = current_profit_per_unit * int(item["expected_monthly_units"])

            summary_rows.append(
                {
                    "Menu Item": item["name"],
                    "Mode": "Recipe" if item["pricing_mode"] == "recipe" else "Cost-only",
                    "Total Cost": round(total_cost, 2),
                    "Current Price": round(float(item["current_selling_price"]), 2),
                    "Recommended Price": round(rec_price, 2),
                    "Price Gap": round(gap, 2),
                    "Current Profit / Unit": round(current_profit_per_unit, 2),
                    "Monthly Profit @ Current Price": round(monthly_profit_at_current, 2),
                    "Health": health_label(gap),
                }
            )

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

        selected_name = st.selectbox(
            "Choose menu item",
            [x["name"] for x in st.session_state["menu_items"]],
        )
        selected_item = next(x for x in st.session_state["menu_items"] if x["name"] == selected_name)

        adjusted_food_cost = apply_wastage(float(selected_item["direct_food_cost"]))
        total_cost = adjusted_food_cost + float(selected_item["packaging_cost"]) + alloc_fixed
        rec_price = recommended_price(total_cost, st.session_state["target_margin_pct"])
        current_price = float(selected_item["current_selling_price"])
        profit_per_unit = current_price - total_cost
        monthly_profit = profit_per_unit * int(selected_item["expected_monthly_units"])
        gap = rec_price - current_price

        left, right = st.columns([1.2, 1])

        with left:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### Profit / loss alert")

            if profit_per_unit < 0:
                st.error(f"You are losing RM {abs(profit_per_unit):.2f} per dish at the current price.")
                st.error(f"Estimated monthly loss: RM {abs(monthly_profit):,.2f}")
            else:
                st.success(f"You earn RM {profit_per_unit:.2f} per dish at the current price.")
                st.success(f"Estimated monthly profit: RM {monthly_profit:,.2f}")

            st.markdown("### Recommendation")
            rec_text = recommendation_text(gap, rec_price, st.session_state["target_margin_pct"])
            if gap > 3.0:
                st.warning(rec_text)
            elif gap > 0.5:
                st.info(rec_text)
            else:
                st.success(rec_text)

            st.markdown("</div>", unsafe_allow_html=True)

        with right:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### Cost structure")
            st.write(f"Food cost after wastage: **RM {adjusted_food_cost:.2f}**")
            st.write(f"Packaging: **RM {float(selected_item['packaging_cost']):.2f}**")
            st.write(f"Allocated fixed cost: **RM {alloc_fixed:.2f}**")
            st.write(f"Total cost per unit: **RM {total_cost:.2f}**")
            st.write(f"Current selling price: **RM {current_price:.2f}**")
            st.write(f"Recommended price: **RM {rec_price:.2f}**")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Margin sensitivity")

        sens_rows = []
        for margin in [20, 25, 30, 35, 40]:
            p = recommended_price(total_cost, margin)
            monthly_profit_est = (p - total_cost) * int(selected_item["expected_monthly_units"])
            sens_rows.append(
                {
                    "Target Margin (%)": margin,
                    "Recommended Price (RM)": round(p, 2),
                    "Monthly Profit Estimate (RM)": round(monthly_profit_est, 2),
                }
            )

        st.dataframe(pd.DataFrame(sens_rows), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("View saved recipe lines for selected menu item"):
            if selected_item["pricing_mode"] == "cost_only":
                st.info("This item was saved in cost-only mode. No recipe details stored.")
            elif selected_item["recipe_items"]:
                st.dataframe(pd.DataFrame(selected_item["recipe_items"]), use_container_width=True, hide_index=True)
            else:
                st.info("No recipe lines available.")

# -------------------------------------------------
# Quick Check
# -------------------------------------------------
elif page == "Quick Check":
    st.markdown('<div class="section-title">Quick price check</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.caption("Fast 30-second check for busy owners who only want a quick answer.")

    q1, q2, q3, q4 = st.columns(4)
    with q1:
        q_cost = st.number_input("Direct food cost (RM)", min_value=0.0, value=10.0, step=0.1)
    with q2:
        q_pack = st.number_input("Packaging (RM)", min_value=0.0, value=0.7, step=0.1)
    with q3:
        q_fixed = st.number_input("Fixed cost per unit (RM)", min_value=0.0, value=3.5, step=0.1)
    with q4:
        q_price = st.number_input("Current selling price (RM)", min_value=0.0, value=12.0, step=0.1)

    q_total = apply_wastage(q_cost) + q_pack + q_fixed
    q_rec = recommended_price(q_total, st.session_state["target_margin_pct"])
    q_profit = q_price - q_total
    q_gap = q_rec - q_price

    a, b, c = st.columns(3)
    with a:
        render_metric_card("Estimated total cost", f"RM {q_total:.2f}")
    with b:
        render_metric_card("Recommended price", f"RM {q_rec:.2f}")
    with c:
        render_metric_card("Current profit / unit", f"RM {q_profit:.2f}")

    if q_profit < 0:
        st.error(f"At the current selling price, the business loses about RM {abs(q_profit):.2f} per unit.")
    elif q_gap > 0.5:
        st.warning(f"Current selling price is below the target. Consider increasing toward RM {q_rec:.2f}.")
    else:
        st.success("Current price is reasonably aligned with the selected target margin.")

    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------
# Import / Export
# -------------------------------------------------
elif page == "Import / Export":
    st.markdown('<div class="section-title">Import / export</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.caption("Use local JSON files if the owner wants full control over their own data.")

    payload = export_payload()
    json_bytes = json.dumps(payload, indent=2).encode("utf-8")

    st.download_button(
        label="Download my data as JSON",
        data=json_bytes,
        file_name="roag_pricing_lab_v03_local_data.json",
        mime="application/json",
    )

    uploaded = st.file_uploader("Load data from local JSON file", type=["json"])
    if uploaded is not None:
        try:
            imported = json.load(uploaded)
            import_payload(imported)
            st.success("Data loaded into the current browser session.")
        except Exception as exc:
            st.error(f"Could not load file: {exc}")

    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------
# Footer
# -------------------------------------------------
st.markdown(
    """
    <div class="footer-box">
        <b>ROAG Pricing Lab v0.3</b> • Privacy-first MVP for Malaysian F&B •
        Ideal for hawkers, small restaurants, cafés, and catering businesses.
    </div>
    """,
    unsafe_allow_html=True,
)
