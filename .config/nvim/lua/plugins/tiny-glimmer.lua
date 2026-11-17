return {
  "rachartier/tiny-glimmer.nvim",
  event = "VeryLazy",
  priority = 10,
  opts = {
    enabled = true,
    disable_warnings = true,
    autoreload = false,
    refresh_interval_ms = 8,
    overwrite = {
      auto_map = true,
      yank = {
        enabled = true,
        default_animation = {
          name = "fade",
          settings = {
            from_color = "#D6B45A",
            to_color = "Normal",
            max_duration = 220,
            min_duration = 160,
          },
        },
      },
      paste = {
        enabled = true,
        default_animation = {
          name = "fade",
          settings = {
            from_color = "#58C4DD",
            to_color = "Normal",
            max_duration = 220,
            min_duration = 160,
          },
        },
        paste_mapping = "p",
        Paste_mapping = "P",
      },
      undo = {
        enabled = true,
        default_animation = {
          name = "fade",
          settings = {
            from_color = "#D6B45A",
            to_color = "Normal",
            max_duration = 220,
            min_duration = 160,
          },
        },
        undo_mapping = "u",
      },
      redo = {
        enabled = true,
        default_animation = {
          name = "fade",
          settings = {
            from_color = "#58C4DD",
            to_color = "Normal",
            max_duration = 220,
            min_duration = 160,
          },
        },
        redo_mapping = "<c-r>",
      },
      search = { enabled = false },
    },
    support = {
      substitute = { enabled = false },
    },
    presets = {
      pulsar = { enabled = false },
    },
    animations = {
      fade = {
        max_duration = 220,
        min_duration = 160,
        easing = "outQuad",
        chars_for_max_duration = 10,
        from_color = "#D6B45A",
        to_color = "Normal",
      },
    },
  },
}
