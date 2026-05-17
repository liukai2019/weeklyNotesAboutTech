OUTPUT := .output
APP := dns-watch
BPFTOOL ?= bpftool
CLANG ?= clang
CC ?= cc
LIBBPF_SRC := ../libbpf-bootstrap/libbpf/src
LIBBPF_OBJ := $(abspath $(OUTPUT)/libbpf.a)
ARCH ?= $(shell uname -m | sed 's/x86_64/x86/' \
	| sed 's/arm.*/arm/' \
	| sed 's/aarch64/arm64/' \
	| sed 's/ppc64le/powerpc/' \
	| sed 's/mips.*/mips/' \
	| sed 's/riscv64/riscv/' \
	| sed 's/loongarch64/loongarch/')

VMLINUX := ../hello-ebpf/vmlinux.h
INCLUDES := -I$(OUTPUT) -I$(LIBBPF_SRC) -I../libbpf-bootstrap/libbpf/include/uapi -I../hello-ebpf -Isrc
USER_CFLAGS := -g -O2 -Wall
USER_LDFLAGS := -lelf -lz

CLANG_BPF_SYS_INCLUDES ?= $(shell $(CLANG) -v -E - </dev/null 2>&1 \
	| sed -n '/<...> search starts here:/,/End of search list./{ s| \(/.*\)|-idirafter \1|p }')

.PHONY: all clean

all: $(APP)

$(OUTPUT):
	mkdir -p $(OUTPUT)

$(LIBBPF_OBJ): $(wildcard $(LIBBPF_SRC)/*.[ch] $(LIBBPF_SRC)/Makefile) | $(OUTPUT)
	$(MAKE) -C $(LIBBPF_SRC) BUILD_STATIC_ONLY=1 \
		OBJDIR=$(dir $@)/libbpf DESTDIR=$(dir $@) \
		INCLUDEDIR= LIBDIR= UAPIDIR= install

$(OUTPUT)/dns_watch.tmp.bpf.o: src/dns_watch.bpf.c src/dns_watch.h $(VMLINUX) | $(OUTPUT)
	$(CLANG) -g -O2 -target bpf -D__TARGET_ARCH_$(ARCH) $(INCLUDES) \
		$(CLANG_BPF_SYS_INCLUDES) -c $< -o $@

$(OUTPUT)/dns_watch.bpf.o: $(OUTPUT)/dns_watch.tmp.bpf.o | $(OUTPUT)
	$(BPFTOOL) gen object $@ $<

$(OUTPUT)/dns_watch.skel.h: $(OUTPUT)/dns_watch.bpf.o | $(OUTPUT)
	$(BPFTOOL) gen skeleton $< > $@

$(OUTPUT)/dns_watch.o: src/dns_watch.c src/dns_watch.h $(OUTPUT)/dns_watch.skel.h $(LIBBPF_OBJ) | $(OUTPUT)
	$(CC) $(USER_CFLAGS) $(INCLUDES) -c src/dns_watch.c -o $@

$(APP): $(OUTPUT)/dns_watch.o $(LIBBPF_OBJ)
	$(CC) $(USER_CFLAGS) $(OUTPUT)/dns_watch.o $(LIBBPF_OBJ) -o $@ $(USER_LDFLAGS)

clean:
	rm -rf $(OUTPUT) $(APP)
