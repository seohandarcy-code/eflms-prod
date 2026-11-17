import { describe, expect, it } from "vitest";
import { mount, RouterLinkStub } from "@vue/test-utils";
import SelectedFacilityCard from "./SelectedFacilityCard.vue";
import type { EquipmentSummary } from "../types/equipment";

const item = (ef_code: string, status: EquipmentSummary["status"]): EquipmentSummary => ({
  equipment_id: 1,
  factory_code: "H1",
  ef_code,
  equipment_name: "x",
  voltage: 0,
  operation_start_time: "2015-03-01",
  pof: 0,
  cof: 0,
  dof: 0,
  total_score: 0,
  status,
  last_diag_date: "2026-01-01",
});

const typeNames = { EF1: "변압기", EF2: "GIS", EF5: "UPS", EF7: "배터리", EF9: "신규설비" };
const items = [item("EF7", "normal"), item("EF7", "review"), item("EF7", "replace"), item("EF1", "normal")];
const mountCard = (selected: string[]) =>
  mount(SelectedFacilityCard, { props: { selected, items, typeNames }, global: { stubs: { RouterLink: RouterLinkStub } } });

describe("SelectedFacilityCard", () => {
  it("shows only a hint when nothing is selected", () => {
    const wrapper = mountCard([]);
    expect(wrapper.text()).toContain("설비유형을 고르면");
    expect(wrapper.find("img").exists()).toBe(false);
  });

  it("shows a large card with picture, summary and counts for one type", () => {
    const wrapper = mountCard(["EF7"]);
    expect(wrapper.text()).toContain("배터리");
    expect(wrapper.text()).toContain("UPS가 정전 때 쓸 전기를 저장해 두는 장치");
    expect(wrapper.text()).toContain("3대");
    expect(wrapper.text()).toContain("점검필요 2");
    expect(wrapper.find("img").attributes("alt")).toBe("배터리 설비 사진");
    // 움직이는 사진: 움직임 줄이기면 PNG, 아니면 WebP, WebP를 못 쓰면 GIF — 받는 동안 PNG 배경
    const sources = wrapper.findAll("source");
    expect(sources.map((s) => s.attributes("media") ?? s.attributes("type"))).toEqual(["(prefers-reduced-motion: reduce)", "image/webp"]);
    expect(sources[0].attributes("srcset")).toContain("ef7.png");
    expect(sources[1].attributes("srcset")).toContain("ef7.webp");
    expect(wrapper.find("img").attributes("src")).toContain("ef7.gif");
    expect(wrapper.find("img").attributes("style")).toContain("ef7.png");
    expect(wrapper.findComponent(RouterLinkStub).props("to")).toEqual({ path: "/guide/facilities", hash: "#ef7" });
  });

  it("shows thumbnails in power-flow order for several types", () => {
    const wrapper = mountCard(["EF5", "EF1", "EF2"]);
    const names = wrapper.findAll(".sfc-thumb-name").map((el) => el.text());
    expect(names).toEqual(["GIS", "변압기", "UPS"]);
    expect(wrapper.text()).toContain("선택한 설비 3");
    // 여러 장도 움직이는 사진(사진마다 WebP 소스)
    expect(wrapper.findAll("source[type='image/webp']").map((s) => s.attributes("srcset"))).toEqual([
      expect.stringContaining("ef2.webp"),
      expect.stringContaining("ef1.webp"),
      expect.stringContaining("ef5.webp"),
    ]);
  });

  it("falls back to an icon for a type without facility info", () => {
    const wrapper = mountCard(["EF9"]);
    expect(wrapper.text()).toContain("신규설비");
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.find(".sfc-noimg").exists()).toBe(true);
  });
});
