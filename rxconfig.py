"""Native Reflex profile; no ORM URL, Redis state or legacy frontend plugins."""
import reflex as rx

config = rx.Config(
    app_name="edgeex_app", loglevel=rx.constants.LogLevel.WARNING, show_built_with_reflex=False,
    state_manager_mode="memory",
    plugins=[rx.plugins.RadixThemesPlugin(theme=rx.theme(
        appearance="dark", accent_color="blue", gray_color="slate",
        radius="medium", scaling="100%", panel_background="solid",
    ))],
    disable_plugins=[rx.plugins.SitemapPlugin],
    frontend_port=3101, backend_port=8101, backend_host="127.0.0.1",
)
