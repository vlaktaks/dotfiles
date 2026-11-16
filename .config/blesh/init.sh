# ble.sh configuration (authoritative dotfiles config)
# Theme-matched syntax highlighting for the active Rundfunk/Kitty palette.
# Loaded via --rcfile from .bashrc when present.

# Keep command input clean: syntax highlighting is the primary goal.
# Disable inline auto-suggestions to avoid distracting ghost text.
bleopt complete_auto_complete=
bleopt complete_auto_history=

# Syntax highlighting faces (truecolor, restrained Rundfunk-inspired palette)
ble-face -s syntax_default            fg=#d7dde8
ble-face -s syntax_command            fg=#59d9e6
ble-face -s syntax_quoted             fg=#7ee787
ble-face -s syntax_quotation          fg=#7ee787
ble-face -s syntax_escape             fg=#ff6ac1
ble-face -s syntax_expr               fg=#7be8f2
ble-face -s syntax_error              fg=#ff5c7a
ble-face -s syntax_varname            fg=#ffd479
ble-face -s syntax_delimiter          fg=#8b98aa
ble-face -s syntax_param_expansion    fg=#ffd479
ble-face -s syntax_history_expansion  fg=#ffd479,bold
ble-face -s syntax_function_name      fg=#d6b45a,bold
ble-face -s syntax_comment            fg=#3a4352
ble-face -s syntax_glob               fg=#56e6d8
ble-face -s syntax_brace              fg=#56e6d8
ble-face -s syntax_tilde              fg=#59d9e6
ble-face -s syntax_document           fg=#9bf0a3
ble-face -s syntax_document_begin     fg=#9bf0a3,bold

# Command word classification
ble-face -s command_builtin           fg=#59d9e6
ble-face -s command_builtin_dot       fg=#ff5c7a,bold
ble-face -s command_alias             fg=#56e6d8
ble-face -s command_function          fg=#d6b45a
ble-face -s command_file              fg=#7ee787
ble-face -s command_keyword           fg=#ff6ac1
ble-face -s command_jobs              fg=#ff6ac1
ble-face -s command_directory         fg=#7be8f2,underline

# Arguments / filenames
ble-face -s argument_option           fg=#56e6d8
ble-face -s argument_error            fg=#ff5c7a,underline
ble-face -s filename_directory        fg=#7be8f2,underline
ble-face -s filename_directory_sticky fg=#f4f8ff,bg=#26313d,underline
ble-face -s filename_link             fg=#56e6d8,underline
ble-face -s filename_orphan           fg=#ff5c7a,underline
ble-face -s filename_executable       fg=#7ee787
ble-face -s filename_other            fg=#d7dde8
ble-face -s filename_warning          fg=#ff5c7a,underline

# Variable/name faces (subtle distinctions)
ble-face -s varname_array             fg=#ffd479
ble-face -s varname_empty             fg=#8b98aa
ble-face -s varname_export            fg=#ffd479
ble-face -s varname_expr              fg=#ffd479
ble-face -s varname_hash              fg=#ffd479
ble-face -s varname_new               fg=#ffd479
ble-face -s varname_number            fg=#ffd479
ble-face -s varname_readonly          fg=#ffd479
ble-face -s varname_transform         fg=#ffd479
ble-face -s varname_unset             fg=#3a4352

# Completion/menu (restrained)
ble-face -s auto_complete             fg=#3a4352
ble-face -s menu_filter_input         fg=#101216,bg=#59d9e6
ble-face -s region                    bg=#26313d,fg=#f4f8ff
ble-face -s region_insert             fg=#59d9e6,bg=#26313d
ble-face -s disabled                  fg=#3a4352
