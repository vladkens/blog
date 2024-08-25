---
title: How to get macOS power metrics with Rust?
slug: powermetrics-macos
date: 2024-09-13
taxonomies:
  tags: ["rust", "macos", "cli"]
---

In this post, I’m going to talk about how [macmon](https://github.com/vladkens/macmon) works, specifically where it gets system metrics.

MacOS has a built-in `powermetics` utility that can show the current CPU core frequencies, utilisation, and power consumption. This program should take these values from the system somewhere. So the first thing to check is what shared libraries and function calls (symbols) are used.

There are several programs can do this:

- `otool` — show list of shared libraries
- `nm` — see the list of used symbols
- `strings` — just prints all strings from a binary file, but it may be useful to understand what is going on in the program.

```text
> otool -L /usr/bin/powermetrics
 /usr/lib/libIOReport.dylib (compatibility version 1.0.0, current version 1.0.0)
 /usr/lib/libpmsample.dylib (compatibility version 1.0.0, current version 2.0.0)
 /usr/lib/libpmenergy.dylib (compatibility version 1.0.0, current version 2.0.0)
 /System/Library/Frameworks/IOKit.framework/Versions/A/IOKit (compatibility version 1.0.0, current version 275.0.0)
...

> nm -a /usr/bin/powermetrics
/usr/bin/powermetrics (for architecture arm64e):
  ...
  U _IOPMCopyPowerStateInfo
  U _IORegistryEntryCreateCFProperties
  U _IORegistryEntryCreateCFProperty
  U _IORegistryEntryFromPath
  ...
```

This data provides some starting point. Next I just did a search on Github to see how these libs might have been used in other repositories.

## Getting CPU / GPU Usage

The first thing I found is that macOS has an `IOReport` shared library that returns a lot of hardware information. Including it can do sampling and return CPU/GPU & energy usage.

`IOReport` operates on a subscription basis. It is possible to select interesting data channels (or all available) and perform sampling on it in order to obtain actual metrics. The channel has a group / subgroup name (sometimes may not exist). I’m interesting in “Energy Model”, “CPU Stats” / “CPU Core Performance States” and “GPU Stats” / “GPU Performance States”. These values were found by comparing available channels names with the list of those strings used in `powermetrics` (`strings /usr/bin/powermetrics`).

To subscribe to a channel and receive updates, it is first necessary to get internal channel struct as `CFDictionary` using `IOReportCopyChannelsInGroup` and merge all the dicts into one using `IOReportMergeChannels`. Then merged dictionary can be used to create an subscription using `IOReportCreateSubscription`. Once subscription object obtained, updates can be received with `IOReportCreateSamples` and `IOReportCreateSamplesDelta`. All together it looks something like this:

```rust
// simplified code without error handling
use std::ptr::null;

let mut channels = vec![];
channels.push(IOReportCopyChannelsInGroup("Energy Model", null(), 0, 0, 0));
channels.push(IOReportCopyChannelsInGroup("CPU Stats", "CPU Core Performance States", 0, 0, 0));

let chan = channels[0];
for i in 1..channels.len() {
  IOReportMergeChannels(chan, channels[i], null());
}

let size = CFDictionaryGetCount(chan);
let chan = CFDictionaryCreateMutableCopy(kCFAllocatorDefault, size, chan);

let mut subs: MaybeUninit<CFMutableDictionaryRef> = MaybeUninit::uninit();
IOReportCreateSubscription(std::ptr::null(), chan, s.as_mut_ptr(), 0, std::ptr::null());
subs.assume_init();

let sample1 = IOReportCreateSamples(subs, chan, null());
std::thread::sleep(std::time::Duration::from_millis(100)); // 100ms
let sample2 = IOReportCreateSamples(subs, chan, null());

let rs = IOReportCreateSamplesDelta(sample1, sample2, null());
CFShow(rs);

// rs is CFDictionary, so we can read metrics by keys from it
```

The basic dict functions are exported from [core_foundation](https://crates.io/crates/core-foundation) crate. `IOReport` functions are C-bindings to a private macOS API:

```rust
#[link(name = "IOReport", kind = "dylib")]
extern "C" {
  fn IOReportCopyChannelsInGroup(a: CFStringRef, b: CFStringRef, c: u64, d: u64, e: u64) -> CFDictionaryRef;
  fn IOReportMergeChannels(a: CFDictionaryRef, b: CFDictionaryRef, nil: CFTypeRef);
  fn IOReportCreateSubscription(a: CVoidRef, b: CFMutableDictionaryRef, c: *mut CFMutableDictionaryRef, d: u64, b: CFTypeRef) -> IOReportSubscriptionRef;
  fn IOReportCreateSamples(a: IOReportSubscriptionRef, b: CFMutableDictionaryRef, c: CFTypeRef) -> CFDictionaryRef;
  fn IOReportCreateSamplesDelta(a: CFDictionaryRef, b: CFDictionaryRef, c: CFTypeRef) -> CFDictionaryRef;
}
```

Full implementation can be found [here](https://github.com/vladkens/macmon/blob/v0.2.2/src/sources.rs#L478).

_Note: For CPU I get values separately for each core. In general, there is also a group “CPU Complex Performance States” to get values for the whole cluster at once, but the group results sometimes show 100% load of the cluster, when in reality there is no load. This is caused by some internal bug. For GPU there is no information for each core separately, so the load information is obtained for the whole GPU at once — good luck no errors were noticed._

## Parsing CPU / GPU Usage

`IOReportCreateSamplesDelta` returns an object with one `IOReportChannels` field, which containts array of metrics objects. Each metrics object have `group` and `subgroup` (on which subscription was created), and extra fields: `channel` name, value `unit` and `value` itself.

The values for “CPU Stats” / “GPU Stats” are returned in array of tuples (string, int):

- string: frequency level name (first always IDLE)
- int: time been on this level (should be in nanoseconds, but not sure)

In general, internally CPU can work at different frequencies and voltages. The values of these frequencies are known in advance and are always the same. Under load CPU works at higher levels (higher frequency, higher voltage). During idle work it constantly jumps between modes (in any case OS always has some background activity). Simple tasks are mostly executed on E-cluster, more complex ones are switched to P-cluster.

Each cluster has different DVFS config (Dynamic Voltage and Frequency Scaling), but all cores within same cluster uses same DVFS config. Same approach is used for GPUs.

Usually GUI interfaces show single number as current core frequency, but in reality it is calculated as average of time each core work on DVFS level. So the average frequency of a core can be calculated like this:

```rust
// predefined DVFS values for E-cluster
let frequencies = [600, 912, 1284, 1752, 2004, 2256, 2424]; // 7 items
// time was on each level (first value is idle)
let residencies = [17563069, 0, 5787276, 156965, 419037, 100647, 106031, 41735]; // 8 items

let total_time = residencies.iter().sum::<u64>();
let usage_time = residencies.iter().skip(1).sum::<u64>();

let mut freq = 0f64;
for i in 0..frequencies.len() {
 let percent = residencies[i + 1] as f64 / usage_time as f64;
 freq += percent * frequencies[i] as f64;
}

println!("E-cluster freq: {:.2} MHz", freq);
```

DVFS values for target system can be read from `AppleARMIODevice`. Full code can be found [here](https://github.com/vladkens/macmon/blob/v0.2.2/src/sources.rs#L459). For M1/M2/M3 processors looks names are: `voltage-states1-sram` for E-Cluster, `voltage-states5-sram` for P-Cluster and `voltage-states9` for GPU. For Max / Ultra chips is also exists `voltage-states11-sram` or something like this, because this chips have two or more P-Clusters but fortunately this values are same for all clusters of same group (at least for now).

## Parsing Energy Usage

In the channel earlier, we also asked for metrics for the “Energy Model” group. These are easier to read because it’s just a number. Value unit can be `mJ / uJ / nJ`, so it just needs to be converted to Watts. This is easily done using the formula: `P(W) = E(J) / t(s)`, where `s` is sampling time. Full code [here](https://github.com/vladkens/macmon/blob/v0.2.2/src/metrics.rs#L249).

```rust
let joules_raw = IOReportSimpleGetIntegerValue(metric_dict, 0) as f32;
let joules = match metric_unit.as_str() {
  "mJ" => joules_raw / 1e3f32,
  "uJ" => joules_raw / 1e6f32,
  "nJ" => joules_raw / 1e9f32,
  _ => Err(format!("Unknown energy unit: {}", metric_unit).into()),
};

let sec = (duration as f32 / 1000.0);
let watts = joules / sec;
```

## Getting RAM Usage

Getting RAM / SWAP usage is done via `libc` in principle I think similar to any UNIX-like system. Nothing specific here, except to figure out how to calculate the value in bytes, since internally memory is measured in pages.

MacOS uses the [`vm_statistics64`](https://opensource.apple.com/source/xnu/xnu-1456.1.26/osfmk/mach/vm_statistics.h.auto.html#:~:text=struct%20vm_statistics64) structure, which has quite a few fields. By experimentation I found a value that is similar to what Activity Monitor shows. To get current memory `host_statistics64` need to be called. For total memory available and SWAP info `sysconf` call is enough. Full code can be found [here](https://github.com/vladkens/macmon/blob/v0.2.2/src/sources.rs#L291). Short example with [libc](https://crates.io/crates/libc) crate:

```rust
let mut count: u32 = libc::HOST_VM_INFO64_COUNT as _;
let mut stats = std::mem::zeroed::<libc::vm_statistics64>();

libc::host_statistics64(
  libc::mach_host_self(),
  libc::HOST_VM_INFO64,
  &mut stats as *mut _ as *mut _, // cast to void (untyped) pointer
  &mut count,
);

let page_size_kb = libc::sysconf(libc::_SC_PAGESIZE) as u64;
let usage = page_size_kb * (
  + stats.active_count as u64
  + stats.inactive_count as u64
  + stats.wire_count as u64
  + stats.speculative_count as u64
  + stats.compressor_page_count as u64
  - stats.purgeable_count as u64
  - stats.external_page_count as u64);
```

## Getting Temperature Values

This appeared to be the most complicated part of the program. Initially I wanted to get values for each core separately and show them in a separate tab in the interface. On macOS there are GUI programs (Stats, Macs Fan Control) that can do this, but after a detailed study I realised that the values in these programs are shown by guessing which sensor is responsible for which core.

Temperature value can be obtained from two places: IOHID for M1 on macOS 12–13 and SMC for M1/M2/M3 on macOS 14–15.

`IOHID` approach is simpler — it’s just a function call that returns a `CFDictionary` with values. There seems only [one person in open-source](https://github.com/freedomtan/sensors/blob/master/sensors/sensors.m) who understands how it works, because all other repositories I found referenced it.

SMC (System Management Controller) is more complicated. It works through something similar to RPC calls with large structures where fields are optionally filled in depending on which RPC method called. SMC looks like a more classic approach, but it looks like Apple didn’t have time to implement all the functionality during migration to ARM architecture. To make `macmon` works everywhere, I had to implement both approaches.

`IOHID` implementation can be found [here](https://github.com/vladkens/macmon/blob/v0.2.2/src/sources.rs#L603), there is really nothing to talk about technically, except that the parameter values are found "magically".

In SMC, it is possible to obtain a sensor’s value using a key. The key itself uses FourCC notation, which is essentially `int32` but appears human-readable in code (for example, `Tp01 -> 0x54703031`, `Tp02 -> 0x54703032`, etc.). This key is used to obtain `KeyInfo`, from which `KeyData` can be retrieved. Therefore, to get the sensor value, two RPC calls are needed, which is inefficient and costly. Hence, it is necessary to cache the `KeyInfo` value beforehand.

The SMC initialisation process looks like: obtain all possible keys using the special key `#KEY` (`0x234b4559`), then filter out only those `KeyInfo` that start with `Tp` (CPU related) and `Tg` (GPU related), and then make requests only to them – resulting in one RPC call per sensor.

Since I do not know which sensors correspond to which core or other sensors on the chip, the program simply calculates average of all values per type.

SMC implementation can be found [here](https://github.com/vladkens/macmon/blob/v0.2.2/src/sources.rs#L752) (utility to perform RPC calls), [here](https://github.com/vladkens/macmon/blob/v0.2.2/src/metrics.rs#L83) (initialisation) and [here](https://github.com/vladkens/macmon/blob/v0.2.2/src/metrics.rs#L147) (actual metrics gathering).

## Combine all together

There’s nothing special about this part. Once per second, the current metric values are obtained from sources described above. The only thing worth noting is that SMC is used by default, if its value is not available, then IOHID is used (fallback for M1 on macOS 13). Then these values are combined into a single structure and return to caller.

Then these values are aggregated in the "frontend" code and output to the console using [ratatui](https://crates.io/crates/ratatui) crate or in plain text in raw mode. But this is already a material for a separate article.

---

You can try [macmon](https://github.com/vladkens/macmon) with Homebrew:

```sh
brew install vladkens/tap/macmon
```
