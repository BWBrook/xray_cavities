# 2026-05-21 Kunanyi Via Deep-Server Tailscale Route

## Summary

Barry set up a Tailscale mesh between the home-network MacBook and
`deep-server` (`utas-ubuntu`). Probing confirmed this gives a working
home-network route to `kunanyi`:

```text
MacBook -> Tailscale utas-ubuntu/deep-server -> TPAC jumpbox -> kunanyi
```

This is useful because direct MacBook TCP/22 to `<tpac-jumpbox>` still
hangs from Barry's home network.

## Probe Results

Tailscale saw `utas-ubuntu`:

```text
<tailscale-ip>   utas-ubuntu      BWBrook@  linux
```

Direct home-network TCP from the MacBook to `<tpac-jumpbox>:22` hung and
had to be killed.

From `utas-ubuntu`, TCP/22 to the TPAC jumpbox succeeded:

```text
Connection to <tpac-jumpbox> (<campus-ip>) 22 port [tcp/ssh] succeeded!
```

An end-to-end expect probe then reached:

```text
<kunanyi-login-host>
```

## Local Mac SSH Aliases Added

The MacBook `~/.ssh/config` now includes:

```text
tpac-jumpbox-via-deep
kunanyi-via-deep
```

These aliases use `ProxyJump utas-ubuntu` before the TPAC jumpbox.

## Helper Usage

Run remote commands from home over this route with:

```bash
TPAC_JUMPBOX_ALIAS=tpac-jumpbox-via-deep \
TPAC_CLUSTER_HOST=kunanyi \
scripts/kunanyi/run_on_kunanyi.sh "<remote command>"
```

Use the same route for uploads with:

```bash
TPAC_SCP_HOST=kunanyi-via-deep \
scripts/kunanyi/copy_to_kunanyi.sh <local-path> <remote-path>
```

The TPAC Open OnDemand jumpbox SSH window is still required.

## Job State Observed During Probe

The same route successfully queried the active retry job:

```text
Job Id: 692504.kunanyi-ohpc
Job_Name = c_hi_fg_retry
job_state = R
queue = normal
resources_used.walltime = 00:28:27
Resource_List.select = 80:ncpus=28:mpiprocs=28
Resource_List.walltime = 08:00:00
comment = Job run at Thu May 21 at 22:39 on (n008:ncpus=28)+(n204:ncpus=28)
```

## Interpretation

This confirms a reliable home-network control path independent of Nectar:

- use direct `kunanyi` aliases on campus/`eduroam`
- use `kunanyi-via-deep` / `tpac-jumpbox-via-deep` from home while Tailscale
  and `deep-server` are online
- keep `kunanyi-via-nectar` as a fallback once Nectar is restored
