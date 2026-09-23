<template>
  <section class="min-h-[80vh] flex items-center justify-center bg-gray-100 px-8 scroll-mt-24" id="home">
    <div class="max-w-4xl text-center">

      <h1 class="text-6xl md:text-8xl font-bold leading-tight">
         We Are <br>
         <span class="text-blue-600"> Thimi Tech</span>
      </h1>

      <h1 class="text-3xl md:text-5xl font-bold leading-tight">
        Intelligent Digital<br>
        <span class="text-blue-600">Solutions</span>
      </h1>

      <p class="mt-6 text-lg text-gray-600 max-w-2xl mx-auto">
        We are a team of developers who are passionate about 
        creating innovative solutions for our clients. We are here to transfer
       <span class="font-bold" >Reality to Vision</span> and <strong>Vision to Reality</strong>.
      </p>

      <div class="mt-8 flex justify-center gap-4">
        <button
          @click="$el.ownerDocument.getElementById('services')?.scrollIntoView({ behavior: 'smooth' })"
          class="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700"
        >
        Explore Our Services
        </button >
        <button
          class="rounded-lg border border-gray-300 px-6 py-3 font-semibold hover:bg-white"
        >
          Contact Us
        </button>
      </div>

    </div>
  </section>
</template>