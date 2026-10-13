# Graph Report - nova-backend  (2026-10-13)

## Corpus Check
- 157 files · ~117,469 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .mdc 1, .example 1)

## Summary
- 3005 nodes · 6916 edges · 170 communities (93 shown, 77 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 718 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Imports and Anthropic Types
- Conversation DAO
- Simpl Finances Service
- SQL Migrations Runner
- Agent Loop and Prompt Sources
- Tool Registration Scripts
- Command Line Service
- Meeting Service
- Background Sub-Agents
- Update Delivery State
- Call Delivery Tests
- Claude Service
- GitHub Service
- Create Update Tests
- Hosting Docs
- Memory Retrieval
- Model Selection
- Update DAO
- Coding Service (Mac)
- ElevenLabs TTS
- Settings Controller
- Process Registry
- Process Supervisor
- Fake Services for Tests
- Meeting Controller
- Cursor Service
- Meeting DAO
- Community 27
- Coding Session DAO
- Report Types and Delivery Status
- OpenAI Loop Tests
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 142
- Community 143
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 151
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157
- Community 158
- Community 159
- Community 161
- Community 162
- Community 164
- Community 166

## God Nodes (most connected - your core abstractions)
1. `AgentLoop` - 83 edges
2. `Conversation` - 76 edges
3. `build_service()` - 57 edges
4. `MeetingService` - 52 edges
5. `CodingService` - 47 edges
6. `Responsibility` - 42 edges
7. `Update` - 42 edges
8. `recording_meeting()` - 40 edges
9. `UpdateService` - 39 edges
10. `ClaudeService` - 38 edges

## Surprising Connections (you probably didn't know these)
- `encode()` --indirect_call--> `text()`  [INFERRED]
  mac_agent/novacode/protocol.py → tests/test_sms_controller.py
- `AgentLoop` --uses--> `PromptEnums`  [INFERRED]
  src/harness/agent_loop.py → prompting/prompt_enums.py
- `MeetingService` --uses--> `PromptEnums`  [INFERRED]
  src/service/meeting_service.py → prompting/prompt_enums.py
- `_run_turn()` --uses--> `PromptSourceEnum`  [INFERRED]
  src/controller/call_controller.py → prompting/prompt_source_prompt.py
- `chat_stream()` --uses--> `PromptSourceEnum`  [INFERRED]
  src/controller/nova_controller.py → prompting/prompt_source_prompt.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Mac agent core design principles** — mac_agent_readme_dial_out, mac_agent_readme_sessions_as_threads, mac_agent_readme_git_worktree [EXTRACTED 1.00]
- **Remote access path: Firebase frontend to Cloudflare Tunnel to tower API** — docs_hosting_firebase_hosting, docs_hosting_cloudflare_tunnel, docs_hosting_tower_api [EXTRACTED 0.95]
- **Persisted-action safety rules across foreground and background agents** — prompting_nova_persona_prompt_confirm_persisted_actions, prompting_nova_persona_prompt_clarify_before_executing, prompting_background_agent_prompt_no_outward_actions [INFERRED 0.85]

## Communities (170 total, 77 thin omitted)

### Community 0 - "Imports and Anthropic Types"
Cohesion: 0.11
Nodes (6): MemoryChunk, MemoryMatch, Message, MessageRole, TurnStream, TurnStreamTests

### Community 1 - "Conversation DAO"
Cohesion: 0.08
Nodes (4): ConversationDao, Conversation, ConversationService, ThreadResolutionTests

### Community 2 - "Simpl Finances Service"
Cohesion: 0.11
Nodes (6): SimplApiError, SimplConfigurationError, SimpleFinancesService, response(), SimpleFinancesServiceTest, SimplFinancesToolRegistrationTest

### Community 3 - "SQL Migrations Runner"
Cohesion: 0.07
Nodes (12): main(), migration_files(), ToolUseStarted, _jsonable(), SQLService, AuthenticationTests, forward(), make_request() (+4 more)

### Community 4 - "Agent Loop and Prompt Sources"
Cohesion: 0.07
Nodes (5): PromptSourceEnum, AgentLoop, persist(), _env_flag(), PrefetchedConversationTests

### Community 5 - "Tool Registration Scripts"
Cohesion: 0.11
Nodes (8): main(), main(), ToolDao, Tool, ToolExecutionError, ToolService, FakeToolDao, ToolServiceTests

### Community 6 - "Command Line Service"
Cohesion: 0.07
Nodes (3): CommandLineService, BackgroundTests, ForegroundTests

### Community 8 - "Background Sub-Agents"
Cohesion: 0.08
Nodes (9): BackgroundAgentTests, fake_get_response(), FakeConversationService, FakeMessage, FakeProjectDao, FakeTextBlock, FakeToolDao, FakeUpdateService (+1 more)

### Community 9 - "Update Delivery State"
Cohesion: 0.12
Nodes (3): Update, _env_int(), UpdateDeliveryService

### Community 10 - "Call Delivery Tests"
Cohesion: 0.17
Nodes (8): at(), build_service(), CallDeliveryTests, EmailDeliveryTests, make_update(), QuietHoursTests, SettleCallTests, SmsDeliveryTests

### Community 11 - "Claude Service"
Cohesion: 0.09
Nodes (3): ClaudeService, GenerationKwargsTests, ClaudeServiceMcpKwargsTests

### Community 12 - "GitHub Service"
Cohesion: 0.15
Nodes (4): GithubService, GithubServiceError, _FakeResponse, GithubServiceTests

### Community 13 - "Create Update Tests"
Cohesion: 0.08
Nodes (8): build_service(), CreateUpdateTests, FakeConversationDao, FakeProjectDao, FakeUpdateDao, make_update(), ReportTypeTests, ViewingTests

### Community 14 - "Hosting Docs"
Cohesion: 0.07
Nodes (28): Hosting Nova off the home network, Backend environment variables, Cloudflare Tunnel (nova-tower, cloudflared), Firebase Hosting frontend (nova-voice-nd.web.app), Infobip SMS integration (/sms/inbound), Failed-login lockout policy, Mac coding agent (/ws/coding), MCP OAuth callback (+20 more)

### Community 15 - "Memory Retrieval"
Cohesion: 0.09
Nodes (3): MemoryChunkService, ParseChunksTests, RetrievableQueryTests

### Community 16 - "Model Selection"
Cohesion: 0.10
Nodes (3): _env_flag(), SettingsService, CurrentModelTests

### Community 19 - "ElevenLabs TTS"
Cohesion: 0.11
Nodes (7): _describe_failure(), ElevenLabsService, ElevenLabsRequestTests, _env(), FallbackTests, refused(), ProviderSelectionTests

### Community 20 - "Settings Controller"
Cohesion: 0.09
Nodes (6): get_all_settings(), get_available_models(), get_claude_credits(), ModelSwitchRequest, set_model(), ClaudeCreditsService

### Community 21 - "Process Registry"
Cohesion: 0.15
Nodes (16): _all(), await_ready(), check(), _entry(), kill_tree(), _log_paths(), pid_alive(), port_open() (+8 more)

### Community 22 - "Process Supervisor"
Cohesion: 0.14
Nodes (15): _all(), await_ready(), check(), classify(), _entry(), _log_paths(), port_open(), read_log() (+7 more)

### Community 23 - "Fake Services for Tests"
Cohesion: 0.09
Nodes (9): build_service(), FakeClaudeResponse, FakeClaudeService, FakeConversationService, FakeEmbeddingService, FakeMemoryChunkDao, FakeTextBlock, FetchMemoryTests (+1 more)

### Community 24 - "Meeting Controller"
Cohesion: 0.12
Nodes (13): delete_meeting(), get_active_meeting(), get_meeting(), get_meeting_segments(), list_meetings(), _meeting_error(), regenerate_notes(), _resolve_meeting_id() (+5 more)

### Community 25 - "Cursor Service"
Cohesion: 0.17
Nodes (4): CursorService, CursorServiceError, CursorServiceTests, _FakeResponse

### Community 26 - "Meeting DAO"
Cohesion: 0.13
Nodes (3): MeetingDao, Meeting, MeetingStatus

### Community 27 - "Community 27"
Cohesion: 0.09
Nodes (5): CodeServiceTestCase, EditTests, FakeConversationDao, FakeProjectDao, PathContainmentTests

### Community 28 - "Coding Session DAO"
Cohesion: 0.16
Nodes (3): CodingSessionDao, CodingEvent, CodingSession

### Community 29 - "Report Types and Delivery Status"
Cohesion: 0.18
Nodes (7): DeliveryStatus, ReportType, user_phone_number(), EscapingTests, BadgeOnlyTests, SmsPermanentFailureTests, UndeliverableTypeTests

### Community 30 - "OpenAI Loop Tests"
Cohesion: 0.17
Nodes (7): FakeClient, FakeFunctionCall, FakeResponse, FakeResponsesAPI, FakeTool, FakeToolService, OpenAILoopTests

### Community 32 - "Community 32"
Cohesion: 0.18
Nodes (4): MessageDao, ProjectDao, Project, ProjectService

### Community 35 - "Community 35"
Cohesion: 0.13
Nodes (10): _callback_page(), create_mcp_server(), delete_mcp_server(), list_mcp_servers(), mcp_oauth_callback(), start_mcp_oauth(), update_mcp_server(), get_project() (+2 more)

### Community 37 - "Community 37"
Cohesion: 0.13
Nodes (7): Config, _flag(), load_env_file(), _configure_logging(), main(), _run(), _task()

### Community 38 - "Community 38"
Cohesion: 0.12
Nodes (11): _canonical_wake_text(), chat_stream(), get_nova_power(), get_nova_state(), has_stop_phrase(), normalize_wake_text(), parse_conversation_id(), _partial_is_due() (+3 more)

### Community 39 - "Community 39"
Cohesion: 0.08
Nodes (7): FakeAgentLoop, FakeClaudeService, FakeConversationDao, FakeEmbeddingService, FakeUpdateService, RecoveryTests, ReplyQueue

### Community 40 - "Community 40"
Cohesion: 0.13
Nodes (6): BipConfigurationError, BipRequestError, is_permanent_bip_error(), normalize_phone_number(), SmsRecipientError, NormalizationTests

### Community 41 - "Community 41"
Cohesion: 0.11
Nodes (3): MeetingChunkDao, MeetingChunk, EmbeddingService

### Community 42 - "Community 42"
Cohesion: 0.13
Nodes (6): MeetingSegment, ChunkingTests, FinalizeTests, NotesTests, NotesUseNoToolsTests, TranscriptTests

### Community 44 - "Community 44"
Cohesion: 0.19
Nodes (4): Responsibility, at(), CheckForResponsibilitiesTests, DueTests

### Community 45 - "Community 45"
Cohesion: 0.18
Nodes (5): McpOAuthService, _now(), _origin(), _path(), CompleteAndRefreshTests

### Community 46 - "Community 46"
Cohesion: 0.16
Nodes (5): ConversationResolutionTests, make_update(), OpeningPromptTests, TwiMLTests, form()

### Community 47 - "Community 47"
Cohesion: 0.14
Nodes (5): build_service(), FakeProjectDao, RetrievalTests, StartMeetingTests, StopMeetingTests

### Community 48 - "Community 48"
Cohesion: 0.17
Nodes (8): main(), _hotwords(), _load_parakeet(), missing_cuda_libraries(), _nvidia_wheel_dll_dirs(), _platform_default_provider(), _resolve_whisper_device(), _setup_cuda_libraries()

### Community 49 - "Community 49"
Cohesion: 0.13
Nodes (10): mint_relay_token(), _opening_prompt(), relay_socket(), start_turn(), run_after_previous(), _resolve_conversation_id(), _run_turn(), _signing_key() (+2 more)

### Community 51 - "Community 51"
Cohesion: 0.17
Nodes (5): DeleteMeetingTests, FollowUpTests, explode(), recording_meeting(), UpdateMeetingTests

### Community 52 - "Community 52"
Cohesion: 0.20
Nodes (5): build_service(), FakeHttp, InfobipRequestTests, RecipientAllowlistTests, SendSmsTests

### Community 53 - "Community 53"
Cohesion: 0.15
Nodes (6): AuthGate, bearer_token(), _header(), is_exempt(), build_app(), ExemptionTests

### Community 56 - "Community 56"
Cohesion: 0.14
Nodes (6): describe_twilio_error(), is_permanent_twilio_error(), SimpleNamespace_Exception, TwilioErrorClassificationTests, reject(), flake()

### Community 58 - "Community 58"
Cohesion: 0.15
Nodes (12): adopt_claude_thread(), _authorized(), coding_socket(), coding_status(), get_coding_session(), list_claude_threads(), list_coding_sessions(), read_claude_thread() (+4 more)

### Community 59 - "Community 59"
Cohesion: 0.17
Nodes (3): ConversationLoopStreamTests, fake_stream(), EventStreamTests

### Community 60 - "Community 60"
Cohesion: 0.20
Nodes (7): fake_stream(), fake_stream(), FakeMessage, fake_stream(), StatusTextTests, fake_stream(), fake_stream()

### Community 61 - "Community 61"
Cohesion: 0.15
Nodes (4): NovaService, OpenAITTS, _requested_provider(), TTSService

### Community 64 - "Community 64"
Cohesion: 0.19
Nodes (5): classify(), _clip(), _resolve_cwd(), run(), _scratch_pair()

### Community 67 - "Community 67"
Cohesion: 0.16
Nodes (6): _comparable(), is_repeat(), _plain_text(), strip_speak_tags(), IsRepeatTests, StripSpeakTagsTests

### Community 68 - "Community 68"
Cohesion: 0.19
Nodes (10): suffix_for_mime(), transcribe_serialized(), send_assistant_text(), _send_locked(), stream_tts_audio(), transcribe_socket(), emit_partial_transcript(), run_speculative_transcription() (+2 more)

### Community 70 - "Community 70"
Cohesion: 0.13
Nodes (8): AgentLoopMcpTests, fake_stream(), fake_stream(), FakeBlock, FakeConversationService, FakeMcpService, FakeMessage, FakeToolDao

### Community 71 - "Community 71"
Cohesion: 0.17
Nodes (7): _client_ip(), current_session(), list_sessions(), login(), logout(), logout_all(), BadCredentials

### Community 72 - "Community 72"
Cohesion: 0.21
Nodes (3): McpServer, _b64url(), _parse_expiry()

### Community 73 - "Community 73"
Cohesion: 0.13
Nodes (3): AuthenticateTests, AuthServiceTestCase, LoginTests

### Community 75 - "Community 75"
Cohesion: 0.15
Nodes (3): GateTestCase, HttpGateTests, WebSocketGateTests

### Community 76 - "Community 76"
Cohesion: 0.16
Nodes (4): CountingService, FakeConversationService, FakeToolDao, fake_stream()

### Community 77 - "Community 77"
Cohesion: 0.14
Nodes (4): _allowed_origins(), lifespan(), _broadcast(), face_socket()

### Community 78 - "Community 78"
Cohesion: 0.18
Nodes (4): _as_int(), _flatten(), _is_prose(), _ms_to_iso()

### Community 79 - "Community 79"
Cohesion: 0.16
Nodes (4): endpoint_decision(), _endpoint_scale(), EndpointDecision, silence_budget_ms()

### Community 80 - "Community 80"
Cohesion: 0.23
Nodes (3): basic(), InboundSecretTests, SenderAllowlistTests

### Community 81 - "Community 81"
Cohesion: 0.23
Nodes (3): FakeToolUseBlock, SpokenTrackTests, fake_stream()

### Community 83 - "Community 83"
Cohesion: 0.17
Nodes (3): build_service(), FakeMcpServerDao, McpServerServiceTests

### Community 87 - "Community 87"
Cohesion: 0.23
Nodes (7): create(), _git(), remove(), resolve_repo(), slugify(), Workspace, WorktreeError

### Community 88 - "Community 88"
Cohesion: 0.17
Nodes (3): BipService, _describe_response_error(), _parse_number_list()

### Community 90 - "Community 90"
Cohesion: 0.27
Nodes (3): stream(), StreamedSpeechTests, fake_stream()

### Community 92 - "Community 92"
Cohesion: 0.26
Nodes (5): build_memory_service(), FakeEmbeddingService, FakeMemoryChunkDao, match(), RetrieveContextTests

### Community 93 - "Community 93"
Cohesion: 0.19
Nodes (4): build_service(), FakeProjectDao, FakeUpdateService, WindowTests

### Community 96 - "Community 96"
Cohesion: 0.27
Nodes (7): backend_url(), close_current_conversation(), fetch_conversation_info(), fetch_health(), fetch_projects(), fetch_tools(), stream_reply()

### Community 97 - "Community 97"
Cohesion: 0.16
Nodes (14): Nova code agent (Mac) README, Anthropic API key stripping, Mac dials out design, Per-session git worktree, Known limits (awake Mac, bounded replay, cache cost), launchd install and menu app, Mac code agent daemon, NOVA_CODE_TOKEN shared secret (+6 more)

### Community 98 - "Community 98"
Cohesion: 0.20
Nodes (5): _handle_inbound(), _is_stale(), resolve_sms_conversation(), _run_sms_turn(), ConversationClosedError

### Community 101 - "Community 101"
Cohesion: 0.23
Nodes (6): BeginFlowTests, fake_get(), fake_post(), fake_post(), fake_post(), FakeResponse

### Community 103 - "Community 103"
Cohesion: 0.19
Nodes (4): AuthNotConfigured, _hash_token(), LockedOut, _now()

### Community 104 - "Community 104"
Cohesion: 0.23
Nodes (4): has_wake_phrase(), split_wake_phrase(), SplitWakePhraseTests, WakePhraseTests

### Community 105 - "Community 105"
Cohesion: 0.18
Nodes (3): row_to_session(), LockoutTests, RowConversionTests

### Community 109 - "Community 109"
Cohesion: 0.27
Nodes (5): close_conversation(), get_conversation(), get_conversation_messages(), _parse_uuid(), _project_payload()

### Community 110 - "Community 110"
Cohesion: 0.26
Nodes (4): drop_hallucination(), DropHallucinationTests, _segment(), WhisperSegmentFilterTests

### Community 111 - "Community 111"
Cohesion: 0.23
Nodes (3): ConnectorFilteringTests, FakeDao, oauth_server()

### Community 113 - "Community 113"
Cohesion: 0.22
Nodes (5): _contained(), make_guard(), can_use_tool(), health(), root()

### Community 114 - "Community 114"
Cohesion: 0.25
Nodes (4): deliver(), _clamp(), clamp_spoken(), ClampSpokenTests

### Community 117 - "Community 117"
Cohesion: 0.31
Nodes (3): host_environment_prompt(), _host_kind(), _machine_line()

### Community 119 - "Community 119"
Cohesion: 0.27
Nodes (5): answer_call(), call_status(), _escape(), _twiml(), _verified_form()

### Community 120 - "Community 120"
Cohesion: 0.22
Nodes (4): list_unviewed_updates(), list_updates(), mark_all_updates_viewed(), mark_update_viewed()

### Community 124 - "Community 124"
Cohesion: 0.20
Nodes (5): FakeConversationService, FakeMessage, FakeTextBlock, FakeToolDao, fake_stream()

### Community 125 - "Community 125"
Cohesion: 0.31
Nodes (6): build_jobs(), _run_check_for_responsibilities(), _run_deliver_pending_updates(), _run_process_conversations(), run_worker(), ScheduledJob

### Community 126 - "Community 126"
Cohesion: 0.36
Nodes (4): cut_clips(), default_audio(), load(), main()

### Community 128 - "Community 128"
Cohesion: 0.31
Nodes (4): _authorize(), inbound_sms(), inbound_sms_with_path_token(), _receive()

### Community 133 - "Community 133"
Cohesion: 0.39
Nodes (3): _artifact_for(), encode(), _truncate()

### Community 134 - "Community 134"
Cohesion: 0.29
Nodes (3): kill_tree(), pid_alive(), _prune()

### Community 143 - "Community 143"
Cohesion: 0.29
Nodes (3): event_source(), sse_event(), iter_in_thread()

### Community 150 - "Community 150"
Cohesion: 0.60
Nodes (5): meeting_socket(), capture_loop(), flush_tail(), send(), _transcribe_tail()

## Ambiguous Edges - Review These
- `TTS conversion enhancer prompt (empty)` → `Voice mode tone guidelines`  [AMBIGUOUS]
  prompting/tts_conversion_enhancer_prompt.txt · relation: conceptually_related_to

## Knowledge Gaps
- **20 isolated node(s):** `install.sh script`, `uninstall.sh script`, `nova-backend`, `Mac dials out design`, `Per-session git worktree` (+15 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 972 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **77 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `TTS conversion enhancer prompt (empty)` and `Voice mode tone guidelines`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `AgentLoop` connect `Agent Loop and Prompt Sources` to `Imports and Anthropic Types`, `Conversation DAO`, `Tool Registration Scripts`, `Meeting Service`, `Background Sub-Agents`, `Claude Service`, `Memory Retrieval`, `Update DAO`, `Community 151`, `Community 155`, `Report Types and Delivery Status`, `Community 34`, `Community 38`, `Community 43`, `Community 49`, `Community 50`, `Community 57`, `Community 59`, `Community 63`, `Community 64`, `Community 65`, `Community 66`, `Community 70`, `Community 76`, `Community 81`, `Community 82`, `Community 90`, `Community 98`, `Community 100`, `Community 112`, `Community 124`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Are the 31 inferred relationships involving `AgentLoop` (e.g. with `PromptEnums` and `PromptSourceEnum`) actually correct?**
  _`AgentLoop` has 31 INFERRED edges - model-reasoned connections that need verification._
- **What connects `install.sh script`, `uninstall.sh script`, `nova-backend` to the rest of the system?**
  _20 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Imports and Anthropic Types` be split into smaller, more focused modules?**
  _Cohesion score 0.1063973063973064 - nodes in this community are weakly interconnected._
- **Why does `ClaudeService` connect `Claude Service` to `Imports and Anthropic Types`, `Agent Loop and Prompt Sources`, `Community 165`, `Meeting Service`, `Community 41`, `Memory Retrieval`, `Community 144`, `Model Selection`, `Settings Controller`, `Community 63`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `Conversation` (e.g. with `_is_stale()` and `ConversationDao`) actually correct?**
  _`Conversation` has 17 INFERRED edges - model-reasoned connections that need verification._