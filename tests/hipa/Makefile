SIZE ?= 32

all:
	nvcc -ccbin=$(CXX) -O3 -arch=sm_80 host-initiated-peer-access.cu -o hipa

ptx:
	nvcc -ccbin=$(CXX) --ptx -O3 -arch=sm_80 host-initiated-peer-access.cu -o hipa.ptx

clean:
	rm -f hipa hipa.ptx

run:
	@rm -f *.zst
	@rm -rf *.txt
	@NOBANNER=1 KERNEL_NAME="simple_kernel" LD_PRELOAD=${SNOOPIE_PATH} ./hipa -n $(SIZE)

run_async:
	@rm -f *.zst
	@NOBANNER=1 KERNEL_NAME="simple_kernel" LD_PRELOAD=${SNOOPIE_PATH} ./hipa -n $(SIZE) -a
