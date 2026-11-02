"""The first load of Home: no empty plate silhouettes, and no downloads nobody needs."""

import pytest
from playwright.sync_api import expect

PLATE_IMAGE = "**/static/weightplate.webp"


def test_plates_stay_hidden_until_their_image_arrives(signed_in_page):
    page = signed_in_page
    held = []
    page.route(PLATE_IMAGE, lambda route: held.append(route))
    page.goto("/", wait_until="domcontentloaded")
    page.wait_for_function("document.querySelector('.mp-plates-section') !== null")
    expect(page.locator("#start-plate")).to_be_hidden()

    page.wait_for_timeout(300)
    assert held, "the plate image should have been requested"
    for route in held:
        route.continue_()
    page.unroute(PLATE_IMAGE)
    expect(page.locator("#start-plate")).to_be_visible()


@pytest.mark.allow_page_errors
def test_plates_still_appear_if_their_image_fails(signed_in_page):
    page = signed_in_page
    page.route(PLATE_IMAGE, lambda route: route.abort())
    page.goto("/")
    expect(page.locator("#start-plate")).to_be_visible()


def test_plates_appear_right_away_when_returning_to_home(signed_in_page):
    page = signed_in_page
    page.goto("/")
    expect(page.locator("#start-plate")).to_be_visible()
    page.evaluate("appRouter.navigate('/workouts')")
    page.wait_for_url("**/workouts")
    page.evaluate("appRouter.navigate('/')")
    page.wait_for_url("**/")
    expect(page.locator("#start-plate")).to_be_visible()
    expect(page.locator(".mp-plates-section")).not_to_have_class("mp-plates-section plates-fade-in plates-ready")


def test_home_skips_images_that_are_not_shown(signed_in_page):
    page = signed_in_page
    requested = []
    page.on("request", lambda r: requested.append(r.url))
    page.goto("/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    for hidden in ("profile2button.png", "profile3button.png", "profile4button.png", "healthbar.png"):
        assert not any(hidden in url for url in requested), f"{hidden} shouldn't download on Home"
    assert any("profilebutton.png" in url for url in requested)


def test_profile_picker_images_load_when_it_opens(signed_in_page):
    page = signed_in_page
    page.goto("/")
    page.wait_for_load_state("networkidle")
    page.locator("#profile-btn").click()
    page.locator("#menu-modal .menu-modal-btn", has_text="Settings").click()
    with page.expect_response("**/static/profile2button.png"):
        page.locator("#change-pic-btn").click()
    expect(page.locator('.pic-option[data-pic="2"] img')).to_be_visible()
