all:	four-gpus_compile four-gpus_run

four-gpus_compile:
	g++ -c -Wall -Werror -fPIC wrapper.cpp  -L/usr/local/cuda/lib64 -lcudart -I/usr/local/cuda/include -O3 -o wrapper.o -lineinfo
	nvcc -shared -O3 -o libwrapper.so wrapper.o -lineinfo
	nvcc -ccbin=$(CXX) -O3 -L. -o four-gpus four-gpus.cu -lwrapper -lineinfo
	nvcc -ccbin=$(CXX) --ptx -O3 four-gpus.cu -o four-gpus.ptx -lineinfo
	nvcc -cubin -lineinfo four-gpus.cu
	nvdisasm --print-line-info four-gpus.cubin > memop_to_line.txt

four-gpus_run:
	LD_LIBRARY_PATH=/usr/local/cuda/lib64:.:$$LD_LIBRARY_PATH LD_PRELOAD=../../../src/mem_multigpu/libmem_multigpu.so KERNEL_NAME=all CODE_ATTRIBUTION=1 ./four-gpus
	#LD_LIBRARY_PATH=/usr/local/cuda/lib64:.:$$LD_LIBRARY_PATH LD_PRELOAD=../../src/mem_multigpu/libmem_multigpu.so ./four-gpus

clean:
	rm -f *.so *.o four-gpus *ptx *cubin *txt
