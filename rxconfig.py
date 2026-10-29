"""Native Reflex profile; no ORM URL, Redis state or legacy frontend plugins."""
import reflex as rx

config = rx.Config(
    app_name="edgeex_app", loglevel=rx.constants.LogLevel.WARNING, show_built_with_reflex=False,
    state_manager_mode="memory",
    plugins=[rx.plugins.RadixThemesPlugin(theme=rx.theme(
        # inherit: Radix follows the <html> color-mode class; assets/scada.css maps Radix vars to --am-*.
        appearance="inherit", accent_color="blue", gray_color="gray",
        radius="large", scaling="100%", panel_background="solid",
    ))],
    default_color_mode="dark",  # design_guide §0: dark by default, light by the header toggle
    disable_plugins=[rx.plugins.SitemapPlugin],
    frontend_port=3101, backend_port=8101, backend_host="127.0.0.1",
)
