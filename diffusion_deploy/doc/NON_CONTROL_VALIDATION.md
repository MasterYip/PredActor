# Non-control validation procedures

These procedures validate model loading, inference, DDS state reception, and
the deliberate absence of command publication. They are engineering tests,
not deployment or authorization to move Unitree MuJoCo or a physical G1.

## Capability boundary

A normal build accepts `offline`, `receive-only`, and `no-publish` without
compiling an active command path. The package also supports an explicit
`--with-sdk2 --with-command-publish` build, but none of the commands on this
page select its `control` mode.

## Bounded session config

Keep a test YAML beside the exported YAML so relative resource paths remain
valid. For Unitree MuJoCo use `lo`; for a passive physical-state test use the
operator-confirmed dedicated G1 interface.

```bash
SOURCE_CONFIG=models/g1_cond_diffuse.yaml
TEST_CONFIG=models/g1_cond_diffuse.no-publish.yaml
TEST_INTERFACE=lo
cp "$SOURCE_CONFIG" "$TEST_CONFIG"
python -c 'import pathlib,sys,yaml; p=pathlib.Path(sys.argv[1]); d=yaml.safe_load(p.read_text()); d.setdefault("env",{}).update(execution_mode="no-publish",network_interface=sys.argv[2]); d.setdefault("runner",{})["max_steps"]=600; p.write_text(yaml.safe_dump(d,sort_keys=False))' "$TEST_CONFIG" "$TEST_INTERFACE"
```

## Workstation checks

Receive one DDS state sample without loading the policy:

```bash
./build/run_g1_robot \
  --config models/g1_cond_diffuse.no-publish.yaml \
  --mode receive-only --max-steps 1 --no-fsm
```

Require the runner to report valid state and zero publisher, shutdown, and
publish counters. Then compute a bounded sequence of policy outputs:

```bash
./build/run_g1_robot \
  --config models/g1_cond_diffuse.no-publish.yaml \
  --mode no-publish --device cuda:0 --max-steps 200 --no-fsm
```

The same test config can exercise CLIP/WBG sender plumbing through `run.sh`,
but the generated actions remain internal to the process.

## Jetson installation check

After verifying the immutable release and model checksums as described in the
operator README, run a short offline inference test:

```bash
"$RELEASE/bin/run_g1_robot" \
  --config "$MODEL/deploy_config.yaml" \
  --mode offline --device cuda:0 --max-steps 5 --no-fsm
```

Require a zero exit code and finite actions at every step. Offline mode creates
no DDS state or command channel. A separate receive-only state check may use a
session copy with the dedicated interface and `--max-steps 1`; it must retain
zero publisher counters.

## Source and native guards

```bash
bash test/test_unitree_no_publish_source.sh .
./build/test_unitree_no_publish
```

Both must pass before relying on these procedures as non-control tests. See
[Safety and control status](SAFETY_AND_CONTROL_STATUS.md) for the implementation
gap and the requirements for any future publishing-capable branch.
